import Foundation

extension Notification.Name {
    /// Posted when a request stays 401 even after a token refresh — the session is invalid and the
    /// app should sign out (routing back to the sign-in screen).
    static let apiUnauthorized = Notification.Name("APIUnauthorized")
}

/// Base API client. All network calls go through here — never import URLSession elsewhere.
final class APIClient {
    static let shared = APIClient()

    private let baseURL: URL
    private let session: URLSession
    private var authToken: String?
    private var tokenProvider: (() async -> String?)?

    private init() {
        self.baseURL = URL(string: Self.resolveBaseURL())!
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        self.session = URLSession(configuration: config)
    }

    /// Where the backend lives, resolved per environment:
    /// - `API_BASE_URL` env var always wins (set it in the Xcode scheme to override).
    /// - Simulator: localhost (the Mac's loopback).
    /// - Physical device (DEBUG or Release): the deployed production API, so the phone works off your
    ///   Mac's LAN (over Wi-Fi/cellular). Override to a local Mac (`http://<mac>.local:8000`) per-build
    ///   with the `API_BASE_URL` scheme env var when you want a device build to hit local dev.
    /// - Release: the production API URL. `aps-environment` in TimeSense.entitlements flips to
    ///   `production` automatically for App Store / TestFlight builds.
    ///
    /// Swap `prodBaseURL` for a custom domain (e.g. `https://api.yourdomain.com`) once one is attached
    /// to the Render service.
    private static let prodBaseURL = "https://timesense-api.onrender.com"

    private static func resolveBaseURL() -> String {
        if let env = ProcessInfo.processInfo.environment["API_BASE_URL"], !env.isEmpty {
            return env
        }
        #if targetEnvironment(simulator)
        return "http://localhost:8000"   // local Mac backend for Simulator dev
        #else
        return prodBaseURL               // physical device + Release → the deployed API
        #endif
    }

    func setAuthToken(_ token: String?) {
        authToken = token
    }

    /// Supplies a fresh ID token on demand (e.g. force-refresh via Firebase). Used to recover from a
    /// 401 caused by a missing/stale token (including the launch race where the first request fires
    /// before the token is set) by refreshing and retrying once.
    func setTokenProvider(_ provider: (() async -> String?)?) {
        tokenProvider = provider
    }

    func get<T: Decodable>(_ path: String) async throws -> T {
        try await request(method: "GET", path: path, body: nil as EmptyBody?)
    }

    func post<B: Encodable, T: Decodable>(_ path: String, body: B) async throws -> T {
        try await request(method: "POST", path: path, body: body)
    }

    func patch<B: Encodable, T: Decodable>(_ path: String, body: B) async throws -> T {
        try await request(method: "PATCH", path: path, body: body)
    }

    func put<B: Encodable, T: Decodable>(_ path: String, body: B) async throws -> T {
        try await request(method: "PUT", path: path, body: body)
    }

    func delete(_ path: String) async throws {
        let _: EmptyResponse = try await request(method: "DELETE", path: path, body: nil as EmptyBody?)
    }

    private func request<B: Encodable, T: Decodable>(
        method: String, path: String, body: B?
    ) async throws -> T {
        do {
            return try await perform(method: method, path: path, body: body)
        } catch APIError.unauthorized {
            // Refresh the token once and retry (handles the launch race + expired tokens).
            if let provider = tokenProvider, let fresh = await provider() {
                authToken = fresh
                do {
                    return try await perform(method: method, path: path, body: body)
                } catch APIError.unauthorized {
                    // Still unauthorized after a fresh token → the session is genuinely invalid.
                    NotificationCenter.default.post(name: .apiUnauthorized, object: nil)
                    throw APIError.unauthorized
                }
            }
            NotificationCenter.default.post(name: .apiUnauthorized, object: nil)
            throw APIError.unauthorized
        }
    }

    private func perform<B: Encodable, T: Decodable>(
        method: String, path: String, body: B?
    ) async throws -> T {
        // NB: URL.appending(path:) percent-encodes the whole string as a single path component,
        // which mangles any "?query" (e.g. "?date=...") into "%3Fdate=..." and 404s. Concatenate
        // onto the base's absolute string so query parameters survive.
        guard let url = URL(string: baseURL.absoluteString + path) else {
            throw APIError.invalidResponse
        }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let body {
            request.httpBody = try JSONEncoder.iso8601.encode(body)
        }

        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw APIError.invalidResponse }

        switch http.statusCode {
        case 200...299:
            return try JSONDecoder.iso8601.decode(T.self, from: data)
        case 401:
            throw APIError.unauthorized
        case 403:
            throw APIError.forbidden
        case 422:
            throw APIError.validationError(data)
        default:
            throw APIError.serverError(http.statusCode, data)
        }
    }
}

// MARK: – Supporting types

enum APIError: Error, LocalizedError {
    case invalidResponse
    case unauthorized
    case forbidden
    case validationError(Data)
    case serverError(Int, Data)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:   return "Invalid server response."
        case .unauthorized:      return "Session expired. Please sign in again."
        case .forbidden:         return "You don't have permission to do that."
        case .validationError:   return "Invalid request."
        case .serverError(let code, _): return "Server error (\(code))."
        }
    }
}

private struct EmptyBody: Encodable {}
private struct EmptyResponse: Decodable {}

extension JSONEncoder {
    static let iso8601: JSONEncoder = {
        let e = JSONEncoder()
        e.dateEncodingStrategy = .iso8601
        return e
    }()
}

extension JSONDecoder {
    static let iso8601: JSONDecoder = {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .iso8601
        return d
    }()
}
