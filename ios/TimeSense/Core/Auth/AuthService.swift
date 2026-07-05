#if canImport(FirebaseAuth)
import Foundation
import FirebaseAuth
import FirebaseCore
import GoogleSignIn

/// Owns all Firebase Auth state. Publishes `currentUser` and drives `AppState.isAuthenticated`.
/// All sign-in methods return a `FirebaseUser` whose ID token is immediately handed to `APIClient`.
@MainActor
final class AuthService: ObservableObject {
    @Published private(set) var currentUser: FirebaseAuth.User? = nil
    @Published private(set) var isLoading: Bool = false
    @Published private(set) var error: AuthError? = nil

    private var authStateListenerHandle: AuthStateDidChangeListenerHandle?

    private var unauthorizedObserver: NSObjectProtocol?

    init() {
        // Let APIClient force-refresh a token to recover from a 401 (launch race / expired token).
        APIClient.shared.setTokenProvider {
            try? await Auth.auth().currentUser?.getIDToken(forcingRefresh: true)
        }

        authStateListenerHandle = Auth.auth().addStateDidChangeListener { [weak self] _, user in
            Task { @MainActor in
                self?.currentUser = user
                await self?.refreshTokenIfNeeded(user: user)
            }
        }

        // A 401 that survives a token refresh means the session is genuinely invalid → sign out so
        // the sign-in screen appears and the user can recover (instead of a dead-end error).
        unauthorizedObserver = NotificationCenter.default.addObserver(
            forName: .apiUnauthorized, object: nil, queue: .main
        ) { [weak self] _ in
            Task { @MainActor in self?.signOut() }
        }
    }

    deinit {
        if let handle = authStateListenerHandle {
            Auth.auth().removeStateDidChangeListener(handle)
        }
        if let observer = unauthorizedObserver {
            NotificationCenter.default.removeObserver(observer)
        }
    }

    // MARK: – Sign in

    func signInWithGoogle(presenting viewController: UIViewController) async {
        guard let clientID = FirebaseApp.app()?.options.clientID else { return }
        isLoading = true
        error = nil
        defer { isLoading = false }
        do {
            let config = GIDConfiguration(clientID: clientID)
            GIDSignIn.sharedInstance.configuration = config
            let result = try await GIDSignIn.sharedInstance.signIn(withPresenting: viewController)
            guard let idToken = result.user.idToken?.tokenString else {
                throw AuthError.missingToken
            }
            let credential = GoogleAuthProvider.credential(
                withIDToken: idToken,
                accessToken: result.user.accessToken.tokenString
            )
            try await Auth.auth().signIn(with: credential)
        } catch {
            self.error = .wrap(error)
        }
    }

    func signInWithApple(credential: OAuthCredential) async {
        isLoading = true
        self.error = nil
        defer { isLoading = false }
        do {
            try await Auth.auth().signIn(with: credential)
        } catch {
            self.error = .wrap(error)
        }
    }

    func signInWithEmail(email: String, password: String) async {
        isLoading = true
        self.error = nil
        defer { isLoading = false }
        do {
            try await Auth.auth().signIn(withEmail: email, password: password)
        } catch {
            self.error = .wrap(error)
        }
    }

    func createAccount(email: String, password: String) async {
        isLoading = true
        self.error = nil
        defer { isLoading = false }
        do {
            try await Auth.auth().createUser(withEmail: email, password: password)
        } catch {
            self.error = .wrap(error)
        }
    }

    func signOut() {
        try? Auth.auth().signOut()
        GIDSignIn.sharedInstance.signOut()
        APIClient.shared.setAuthToken(nil)
    }

    func resetPassword(email: String) async {
        isLoading = true
        self.error = nil
        defer { isLoading = false }
        do {
            try await Auth.auth().sendPasswordReset(withEmail: email)
        } catch {
            self.error = .wrap(error)
        }
    }

    private func refreshTokenIfNeeded(user: FirebaseAuth.User?) async {
        guard let user else {
            APIClient.shared.setAuthToken(nil)
            return
        }
        do {
            let token = try await user.getIDToken()
            APIClient.shared.setAuthToken(token)
        } catch {
            self.error = .wrap(error)
        }
    }

    func freshToken() async throws -> String {
        guard let user = Auth.auth().currentUser else { throw AuthError.notAuthenticated }
        return try await user.getIDToken(forcingRefresh: false)
    }
}

enum AuthError: LocalizedError {
    case missingToken
    case notAuthenticated
    case firebase(Error)

    static func wrap(_ error: Error) -> AuthError {
        if let e = error as? AuthError { return e }
        return .firebase(error)
    }

    var errorDescription: String? {
        switch self {
        case .missingToken:      return "Sign-in failed: missing ID token."
        case .notAuthenticated:  return "You are not signed in."
        case .firebase(let e):   return e.localizedDescription
        }
    }
}

#else

import Foundation
import Combine

/// Stub used when Firebase SDK is not linked (e.g. CLI builds without SPM resolution).
@MainActor
final class AuthService: ObservableObject {
    @Published private(set) var currentUser: StubUser? = nil
    @Published private(set) var isLoading: Bool = false
    @Published private(set) var error: AuthError? = nil

    init() {}
    func signInWithGoogle(presenting: AnyObject) async {}
    func signInWithApple(credential: Any) async {}
    func signInWithEmail(email: String, password: String) async {}
    func createAccount(email: String, password: String) async {}
    func signOut() {}
    func resetPassword(email: String) async {}
    func freshToken() async throws -> String { throw AuthError.notAuthenticated }
}

struct StubUser { let uid: String; let email: String? }

enum AuthError: LocalizedError {
    case missingToken, notAuthenticated, other(String)
    static func wrap(_ e: Error) -> AuthError { .other(e.localizedDescription) }
    var errorDescription: String? {
        switch self {
        case .missingToken:    return "Missing token."
        case .notAuthenticated: return "Not signed in."
        case .other(let m):   return m
        }
    }
}

#endif
