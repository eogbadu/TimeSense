import SwiftUI

/// Settings ▸ Connections ▸ Email tasks — review tasks TimeSense detects in recent emails.
///
/// Read-only + explicit: the user grants email-content consent, taps "Scan for tasks", then approves
/// or dismisses each detected item. Nothing becomes a task without approval, and no email is stored
/// beyond the subject/preview shown here.
struct EmailTasksView: View {
    @StateObject private var viewModel = EmailTasksViewModel()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                Text("TimeSense reads recent unread emails (subject and preview only) to suggest tasks. You approve each one — nothing is saved unless you do.")
                    .font(DesignTokens.Typography.footnote)
                    .foregroundColor(DesignTokens.Color.textSecondary)

                if let banner = viewModel.banner {
                    Text(banner)
                        .font(DesignTokens.Typography.footnote)
                        .foregroundColor(DesignTokens.Color.accent)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(DesignTokens.Spacing.md)
                        .cardStyle()
                }

                if !viewModel.hasConsent {
                    consentGate
                } else {
                    scanButton
                    itemsList
                }
            }
            .padding(DesignTokens.Spacing.lg)
        }
        .background(DesignTokens.Color.background)
        .navigationTitle("Email tasks")
        .navigationBarTitleDisplayMode(.inline)
        .task { await viewModel.load() }
    }

    private var consentGate: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            Text("Allow email access")
                .font(DesignTokens.Typography.headline)
                .foregroundColor(DesignTokens.Color.textPrimary)
            Text("We only read recent unread messages, and only the subject + short preview — never the full email, and never to send anything.")
                .font(DesignTokens.Typography.footnote)
                .foregroundColor(DesignTokens.Color.textSecondary)
            Button {
                Task { await viewModel.grantConsent() }
            } label: {
                Text("Allow & continue")
                    .font(DesignTokens.Typography.subheadline.weight(.semibold))
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, DesignTokens.Spacing.md)
                    .background(Capsule().fill(DesignTokens.Color.accent))
            }
        }
        .padding(DesignTokens.Spacing.md)
        .cardStyle()
    }

    private var scanButton: some View {
        Button {
            Task { await viewModel.scan() }
        } label: {
            HStack(spacing: DesignTokens.Spacing.sm) {
                if viewModel.isScanning { ProgressView().tint(.white) }
                Text(viewModel.isScanning ? "Scanning…" : "Scan for tasks")
                    .font(DesignTokens.Typography.headline)
                    .foregroundColor(.white)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, DesignTokens.Spacing.md)
            .background(Capsule().fill(DesignTokens.Color.accent))
        }
        .disabled(viewModel.isScanning)
    }

    @ViewBuilder
    private var itemsList: some View {
        if viewModel.items.isEmpty {
            Text("No detected tasks yet. Tap “Scan for tasks” to check your recent email.")
                .font(DesignTokens.Typography.footnote)
                .foregroundColor(DesignTokens.Color.textSecondary)
                .frame(maxWidth: .infinity, alignment: .center)
                .padding(.top, DesignTokens.Spacing.lg)
        } else {
            ForEach(viewModel.items) { item in
                EmailTaskRow(
                    item: item,
                    onApprove: { Task { await viewModel.approve(item.id) } },
                    onDismiss: { Task { await viewModel.dismiss(item.id) } }
                )
            }
        }
    }
}

private struct EmailTaskRow: View {
    let item: EmailActionItem
    let onApprove: () -> Void
    let onDismiss: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text(item.detectedTitle)
                .font(DesignTokens.Typography.headline)
                .foregroundColor(DesignTokens.Color.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
            Text("\(item.subject) · \(item.sender ?? "Unknown sender")")
                .font(DesignTokens.Typography.caption)
                .foregroundColor(DesignTokens.Color.textSecondary)
                .lineLimit(2)

            HStack(spacing: DesignTokens.Spacing.md) {
                Button(action: onApprove) {
                    Label("Add task", systemImage: "checkmark")
                        .font(DesignTokens.Typography.subheadline.weight(.semibold))
                        .foregroundColor(.white)
                        .padding(.vertical, 8)
                        .padding(.horizontal, 16)
                        .background(Capsule().fill(DesignTokens.Color.accent))
                }
                Button(action: onDismiss) {
                    Text("Dismiss")
                        .font(DesignTokens.Typography.subheadline.weight(.semibold))
                        .foregroundColor(DesignTokens.Color.textSecondary)
                        .padding(.vertical, 8)
                        .padding(.horizontal, 16)
                        .background(Capsule().stroke(DesignTokens.Color.textSecondary.opacity(0.4)))
                }
                Spacer()
            }
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .cardStyle()
    }
}

// MARK: - Model

struct EmailActionItem: Identifiable, Decodable {
    let id: String
    let subject: String
    let sender: String?
    let detectedTitle: String
    let status: String

    enum CodingKeys: String, CodingKey {
        case id
        case subject
        case sender
        case detectedTitle = "detected_title"
        case status
    }
}

// MARK: - View model

@MainActor
final class EmailTasksViewModel: ObservableObject {
    @Published private(set) var items: [EmailActionItem] = []
    @Published private(set) var hasConsent = false
    @Published private(set) var isScanning = false
    @Published private(set) var banner: String?

    func load() async {
        await refreshConsent()
        await reloadPending()
    }

    func grantConsent() async {
        banner = nil
        do {
            let _: ConsentRecordDTO = try await APIClient.shared.post(
                "/api/v1/consent/", body: ConsentBody(consent_type: "email_content", granted: true)
            )
            hasConsent = true
        } catch {
            banner = "Couldn't save your choice. Try again."
        }
    }

    func scan() async {
        banner = nil
        isScanning = true
        defer { isScanning = false }
        do {
            let result: EmailScanResultDTO = try await APIClient.shared.post(
                "/api/v1/email/scan", body: ScanBody()
            )
            await reloadPending()
            banner = Self.scanSummary(scanned: result.scanned, found: result.detected.count)
        } catch APIError.forbidden {
            banner = "Email access isn't allowed yet."
            hasConsent = false
        } catch APIError.serverError(404, _) {
            banner = "Connect Gmail first (Settings ▸ Connections ▸ Gmail)."
        } catch {
            banner = "Couldn't scan right now. Try again."
        }
    }

    func approve(_ id: String) async {
        do {
            let _: EmailActionItem = try await APIClient.shared.post(
                "/api/v1/email/actions/\(id)/confirm", body: EmptyBody()
            )
        } catch {
            banner = "Couldn't add that task. Try again."
        }
        await reloadPending()
    }

    func dismiss(_ id: String) async {
        // reject returns 204 (no body) — tolerate the empty decode, then reload.
        let _: EmptyDecodable? = try? await APIClient.shared.post(
            "/api/v1/email/actions/\(id)/reject", body: EmptyBody()
        )
        await reloadPending()
    }

    private func refreshConsent() async {
        if let c: EffectiveConsentDTO = try? await APIClient.shared.get("/api/v1/consent/") {
            hasConsent = c.consents["email_content"] ?? false
        }
    }

    private static func scanSummary(scanned: Int, found: Int) -> String {
        if scanned == 0 { return "No recent unread emails to scan." }
        let emails = "\(scanned) email\(scanned == 1 ? "" : "s")"
        if found == 0 { return "Scanned \(emails) — no tasks found." }
        return "Scanned \(emails) · found \(found) task\(found == 1 ? "" : "s")."
    }

    private func reloadPending() async {
        if let list: [EmailActionItem] = try? await APIClient.shared.get("/api/v1/email/pending") {
            items = list
        }
    }
}

// MARK: - DTOs

private struct ScanBody: Encodable {}
private struct EmptyBody: Encodable {}
private struct EmptyDecodable: Decodable {}

private struct ConsentBody: Encodable {
    let consent_type: String
    let granted: Bool
}

private struct ConsentRecordDTO: Decodable { let granted: Bool }

private struct EffectiveConsentDTO: Decodable { let consents: [String: Bool] }

private struct EmailScanResultDTO: Decodable {
    let scanned: Int
    let detected: [EmailActionItem]
}
