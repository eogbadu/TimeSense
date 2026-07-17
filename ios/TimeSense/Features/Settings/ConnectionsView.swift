import AuthenticationServices
import SwiftUI

/// Settings ▸ Connections — connect Google Calendar, Outlook, and Slack via OAuth.
///
/// Each "Connect" opens the provider's consent page in an ASWebAuthenticationSession. The backend
/// handles the code→token exchange server-side and redirects to `timesense://integrations/connected`,
/// which the session catches (callbackURLScheme "timesense") and closes.
struct ConnectionsView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var viewModel = ConnectionsViewModel()

    private let providers: [ConnectProvider] = [
        ConnectProvider(id: "google", name: "Google Calendar", systemImage: "calendar",
                        tint: .green, blurb: "Schedule around your Google events."),
        ConnectProvider(id: "microsoft", name: "Outlook Calendar", systemImage: "calendar",
                        tint: .blue, blurb: "Schedule around your Outlook / Microsoft events."),
        ConnectProvider(id: "slack", name: "Slack", systemImage: "message.fill",
                        tint: .purple, blurb: "Turn Slack messages into tasks you can approve."),
        ConnectProvider(id: "gmail", name: "Gmail", systemImage: "envelope.fill",
                        tint: .red, blurb: "Find tasks in recent emails — read-only, you approve each one."),
        ConnectProvider(id: "notion", name: "Notion", systemImage: "doc.text.fill",
                        tint: .green, blurb: "Pull to-dos from a Notion database as tasks you can approve."),
    ]

    var body: some View {
        ScrollView {
            VStack(spacing: DesignTokens.Spacing.lg) {
                Text("Connect the tools you already use. TimeSense only reads what it needs, and calendar changes always ask first.")
                    .font(DesignTokens.Typography.callout)
                    .foregroundColor(DesignTokens.Color.textSecondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, DesignTokens.Spacing.md)
                    .padding(.top, DesignTokens.Spacing.md)

                if appState.isPremium {
                    VStack(spacing: DesignTokens.Spacing.md) {
                        ForEach(providers) { provider in
                            ConnectRow(
                                provider: provider,
                                state: viewModel.state(for: provider.id),
                                onConnect: { Task { await viewModel.connect(provider.id) } },
                                onDisconnect: { Task { await viewModel.disconnect(provider.id) } }
                            )
                        }

                        // Review detected email tasks (after connecting Gmail).
                        NavigationLink(destination: EmailTasksView()) {
                            HStack(spacing: DesignTokens.Spacing.md) {
                                Image(systemName: "tray.full.fill")
                                    .font(.title3)
                                    .foregroundColor(.red)
                                    .frame(width: 40, height: 40)
                                    .background(RoundedRectangle(cornerRadius: 10, style: .continuous).fill(Color.red.opacity(0.14)))
                                VStack(alignment: .leading, spacing: 2) {
                                    Text("Email tasks")
                                        .font(DesignTokens.Typography.headline)
                                        .foregroundColor(DesignTokens.Color.textPrimary)
                                    Text("Scan recent emails and approve the tasks TimeSense finds.")
                                        .font(DesignTokens.Typography.footnote)
                                        .foregroundColor(DesignTokens.Color.textSecondary)
                                }
                                Spacer(minLength: DesignTokens.Spacing.sm)
                                Image(systemName: "chevron.right")
                                    .font(.footnote.weight(.semibold))
                                    .foregroundColor(DesignTokens.Color.textSecondary)
                            }
                            .padding(DesignTokens.Spacing.md)
                            .cardStyle()
                        }
                        .buttonStyle(.plain)
                    }
                } else {
                    Text("Connecting apps is a Premium feature.")
                        .font(DesignTokens.Typography.footnote)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                        .padding(.top, DesignTokens.Spacing.lg)
                }
            }
            .padding(.horizontal, DesignTokens.Spacing.lg)
            .padding(.bottom, DesignTokens.Spacing.xxl)
        }
        .background(DesignTokens.Color.background)
        .navigationTitle("Connections")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            if appState.isPremium { await viewModel.loadStatus() }
        }
    }
}

// MARK: - Row

private struct ConnectRow: View {
    let provider: ConnectProvider
    let state: ConnectState
    let onConnect: () -> Void
    let onDisconnect: () -> Void

    var body: some View {
        HStack(spacing: DesignTokens.Spacing.md) {
            Image(systemName: provider.systemImage)
                .font(.title3)
                .foregroundColor(provider.tint)
                .frame(width: 40, height: 40)
                .background(RoundedRectangle(cornerRadius: 10, style: .continuous).fill(provider.tint.opacity(0.14)))

            VStack(alignment: .leading, spacing: 2) {
                Text(provider.name)
                    .font(DesignTokens.Typography.headline)
                    .foregroundColor(DesignTokens.Color.textPrimary)
                    .lineLimit(1)
                Text(state.subtitle ?? provider.blurb)
                    .font(DesignTokens.Typography.footnote)
                    .foregroundColor(state.isError ? .red : DesignTokens.Color.textSecondary)
                    .lineLimit(2)
            }
            Spacer(minLength: DesignTokens.Spacing.sm)

            trailing
        }
        .padding(DesignTokens.Spacing.md)
        .cardStyle()
    }

    @ViewBuilder
    private var trailing: some View {
        switch state {
        case .connecting, .disconnecting:
            ProgressView()
        case .connected:
            Button(action: onDisconnect) {
                Text("Disconnect")
                    .font(DesignTokens.Typography.subheadline.weight(.semibold))
                    .foregroundColor(provider.tint)
                    .lineLimit(1)
                    .fixedSize(horizontal: true, vertical: false)
                    .padding(.vertical, 8)
                    .padding(.horizontal, 16)
                    .background(Capsule().stroke(provider.tint.opacity(0.6), lineWidth: 1.5))
            }
            .layoutPriority(1)
        default:
            Button(action: onConnect) {
                Text("Connect")
                    .font(DesignTokens.Typography.subheadline.weight(.semibold))
                    .foregroundColor(.white)
                    .padding(.vertical, 8)
                    .padding(.horizontal, 16)
                    .background(Capsule().fill(provider.tint))
            }
        }
    }
}

// MARK: - Model

struct ConnectProvider: Identifiable {
    let id: String
    let name: String
    let systemImage: String
    let tint: Color
    let blurb: String
}

enum ConnectState: Equatable {
    case idle
    case connecting
    case connected
    case disconnecting
    case failed(String)

    var isError: Bool { if case .failed = self { return true }; return false }

    var subtitle: String? {
        switch self {
        case .connected: return "Connected"
        case .connecting: return "Opening sign-in…"
        case .disconnecting: return "Disconnecting…"
        case .failed(let message): return message
        case .idle: return nil
        }
    }
}

// MARK: - View model

@MainActor
final class ConnectionsViewModel: ObservableObject {
    @Published private var states: [String: ConnectState] = [:]
    private let authenticator = WebAuthenticator()

    func state(for provider: String) -> ConnectState { states[provider] ?? .idle }

    /// Disconnect endpoints live on each provider's own router.
    private func disconnectPath(_ provider: String) -> String {
        switch provider {
        case "google", "microsoft": return "/api/v1/calendar/disconnect/\(provider)"
        case "gmail": return "/api/v1/email/disconnect"
        case "slack": return "/api/v1/slack/disconnect"
        case "notion": return "/api/v1/notion/disconnect"
        default: return "/api/v1/integrations/\(provider)/disconnect"
        }
    }

    /// On appear, ask the backend which providers are already connected so we show Disconnect (not
    /// Connect) for those. Leaves any in-flight connecting/failed state untouched.
    func loadStatus() async {
        guard let status: IntegrationsStatus = try? await APIClient.shared.get("/api/v1/integrations/status") else { return }
        for (provider, connected) in status.byProvider where connected {
            if states[provider] == nil || states[provider] == .idle {
                states[provider] = .connected
            }
        }
    }

    func disconnect(_ provider: String) async {
        states[provider] = .disconnecting
        do {
            try await APIClient.shared.delete(disconnectPath(provider))
            states[provider] = .idle
        } catch {
            states[provider] = .failed("Couldn't disconnect. Try again.")
        }
    }

    func connect(_ provider: String) async {
        states[provider] = .connecting
        do {
            let resp: AuthorizeResponse = try await APIClient.shared.get("/api/v1/integrations/\(provider)/authorize")
            guard let url = URL(string: resp.authorizeUrl) else {
                states[provider] = .failed("Couldn't start sign-in.")
                return
            }
            let callback = try await authenticator.authenticate(url: url, callbackScheme: "timesense")
            states[provider] = callback.absoluteString.contains("connected")
                ? .connected
                : .failed("Couldn't connect. Try again.")
        } catch is CancellationError {
            states[provider] = .idle  // no callback returned
        } catch let error as ASWebAuthenticationSessionError where error.code == .canceledLogin {
            states[provider] = .idle  // user dismissed the sheet
        } catch APIError.forbidden {
            states[provider] = .failed("Premium required.")
        } catch APIError.serverError(503, _) {
            states[provider] = .failed("Not available yet.")
        } catch {
            states[provider] = .failed("Couldn't connect. Try again.")
        }
    }
}

private struct AuthorizeResponse: Decodable {
    let authorizeUrl: String
    enum CodingKeys: String, CodingKey { case authorizeUrl = "authorize_url" }
}

private struct IntegrationsStatus: Decodable {
    let google: Bool
    let microsoft: Bool
    let gmail: Bool
    let slack: Bool
    let notion: Bool

    var byProvider: [String: Bool] {
        ["google": google, "microsoft": microsoft, "gmail": gmail, "slack": slack, "notion": notion]
    }
}

// MARK: - Web auth

/// Wraps ASWebAuthenticationSession in an async call and provides the presentation anchor.
@MainActor
final class WebAuthenticator: NSObject, ASWebAuthenticationPresentationContextProviding {
    private var session: ASWebAuthenticationSession?

    func authenticate(url: URL, callbackScheme: String) async throws -> URL {
        try await withCheckedThrowingContinuation { continuation in
            let session = ASWebAuthenticationSession(url: url, callbackURLScheme: callbackScheme) { callbackURL, error in
                if let error {
                    continuation.resume(throwing: error)
                } else if let callbackURL {
                    continuation.resume(returning: callbackURL)
                } else {
                    continuation.resume(throwing: CancellationError())
                }
            }
            session.presentationContextProvider = self
            session.prefersEphemeralWebBrowserSession = false
            self.session = session
            session.start()
        }
    }

    nonisolated func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }
            .flatMap { $0.windows }
            .first { $0.isKeyWindow } ?? ASPresentationAnchor()
    }
}
