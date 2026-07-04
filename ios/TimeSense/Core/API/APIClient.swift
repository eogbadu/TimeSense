import Foundation

/// Base API client. All network calls go through here — never import URLSession elsewhere.
final class APIClient {
    static let shared = APIClient()

    private let baseURL: URL
    private let session: URLSession
    private var authToken: String?

    private init() {
        let base = ProcessInfo.processInfo.environment["API_BASE_URL"] ?? "http://localhost:8000"
        self.baseURL = URL(string: base)!
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        self.session = URLSession(configuration: config)
    }

    func setAuthToken(_ token: String?) {
        authToken = token
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

    func delete(_ path: String) async throws {
        let _: EmptyResponse = try await request(method: "DELETE", path: path, body: nil as EmptyBody?)
    }

    private func request<B: Encodable, T: Decodable>(
        method: String, path: String, body: B?
    ) async throws -> T {
        var request = URLRequest(url: baseURL.appending(path: path))
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
