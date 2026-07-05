import SwiftUI

// MARK: - Profile

struct ProfileSettingsView: View {
    @State private var email = ""
    @State private var displayName = ""
    @State private var loaded = false
    @State private var saving = false
    @State private var saved = false

    private struct UserMe: Decodable {
        let email: String
        let profile: Profile?
        struct Profile: Decodable { let display_name: String? }
    }
    private struct ProfileUpdate: Encodable { let display_name: String }
    private struct ProfileResp: Decodable { let display_name: String? }

    var body: some View {
        Form {
            Section("Account") {
                LabeledContent("Email", value: email.isEmpty ? "—" : email)
            }
            Section("Display name") {
                TextField("Your name", text: $displayName)
                    .textInputAutocapitalization(.words)
            }
            Section {
                Button {
                    Task { await save() }
                } label: {
                    HStack {
                        Text(saved ? "Saved" : "Save changes")
                        Spacer()
                        if saving { ProgressView() }
                        else if saved { Image(systemName: "checkmark").foregroundColor(DesignTokens.Color.success) }
                    }
                }
                .disabled(saving)
            }
        }
        .navigationTitle("Profile")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private func load() async {
        guard !loaded else { return }
        loaded = true
        if let me: UserMe = try? await APIClient.shared.get("/api/v1/users/me") {
            email = me.email
            displayName = me.profile?.display_name ?? ""
        }
    }

    private func save() async {
        saving = true
        defer { saving = false }
        let _: ProfileResp? = try? await APIClient.shared.patch(
            "/api/v1/users/me/profile", body: ProfileUpdate(display_name: displayName)
        )
        saved = true
    }
}

// MARK: - Subscription (read-only status)

struct SubscriptionSettingsView: View {
    @State private var loaded = false
    @State private var isPremium = false
    @State private var status: String?
    @State private var plan: String?
    @State private var trialEnd: String?

    private struct Sub: Decodable {
        let status: String
        let plan: String?
        let trial_end: String?
        let is_premium: Bool
    }

    var body: some View {
        Form {
            Section("Current plan") {
                LabeledContent("Plan", value: isPremium ? "Premium" : "Basic (Free)")
                if let status { LabeledContent("Status", value: status.capitalized) }
                if let plan { LabeledContent("Tier", value: plan.capitalized) }
                if let trialEnd { LabeledContent("Trial ends", value: String(trialEnd.prefix(10))) }
            }
            Section {
                Text(isPremium
                     ? "You have full access to Premium features."
                     : "You're on Basic. Premium unlocks weekly insights, integrations, and more.")
                    .font(DesignTokens.Typography.footnote)
                    .foregroundColor(DesignTokens.Color.textSecondary)
            } footer: {
                Text("Plans and billing are managed through the App Store.")
            }
        }
        .navigationTitle("Subscription")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private func load() async {
        guard !loaded else { return }
        loaded = true
        if let sub: Sub? = try? await APIClient.shared.get("/api/v1/subscriptions/me"), let s = sub {
            isPremium = s.is_premium
            status = s.status
            plan = s.plan
            trialEnd = s.trial_end
        }
    }
}

// MARK: - Notifications

struct NotificationsSettingsView: View {
    @State private var mode = "balanced"
    @State private var loaded = false

    private let modes: [(id: String, title: String, subtitle: String)] = [
        ("gentle", "Gentle", "A few quiet nudges a day"),
        ("balanced", "Balanced", "A helpful rhythm — the default"),
        ("active_coach", "Active coach", "Frequent, proactive check-ins"),
    ]

    private struct UserMe: Decodable { let preferences: Prefs?; struct Prefs: Decodable { let notification_mode: String } }
    private struct Update: Encodable { let notification_mode: String }
    private struct PrefsResp: Decodable { let notification_mode: String }

    var body: some View {
        Form {
            Section {
                ForEach(modes, id: \.id) { m in
                    Button {
                        Task { await set(m.id) }
                    } label: {
                        HStack(spacing: DesignTokens.Spacing.md) {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(m.title).foregroundColor(DesignTokens.Color.textPrimary)
                                Text(m.subtitle)
                                    .font(DesignTokens.Typography.footnote)
                                    .foregroundColor(DesignTokens.Color.textSecondary)
                            }
                            Spacer()
                            if mode == m.id {
                                Image(systemName: "checkmark").foregroundColor(DesignTokens.Color.accent)
                            }
                        }
                    }
                }
            } header: {
                Text("How often should TimeSense reach out?")
            }
        }
        .navigationTitle("Notifications")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private func load() async {
        guard !loaded else { return }
        loaded = true
        if let me: UserMe = try? await APIClient.shared.get("/api/v1/users/me"),
           let m = me.preferences?.notification_mode {
            mode = m
        }
    }

    private func set(_ newMode: String) async {
        let previous = mode
        mode = newMode
        let resp: PrefsResp? = try? await APIClient.shared.patch(
            "/api/v1/users/me/preferences", body: Update(notification_mode: newMode)
        )
        if resp == nil { mode = previous }  // revert on failure
    }
}

// MARK: - Appearance

struct AppearanceSettingsView: View {
    @AppStorage("appTheme") private var appTheme = "system"

    private let options: [(id: String, title: String)] = [
        ("system", "System"), ("light", "Light"), ("dark", "Dark"),
    ]
    private struct Update: Encodable { let theme: String }
    private struct PrefsResp: Decodable { let theme: String }

    var body: some View {
        Form {
            Section {
                ForEach(options, id: \.id) { opt in
                    Button {
                        appTheme = opt.id
                        Task {
                            let _: PrefsResp? = try? await APIClient.shared.patch(
                                "/api/v1/users/me/preferences", body: Update(theme: opt.id)
                            )
                        }
                    } label: {
                        HStack {
                            Text(opt.title).foregroundColor(DesignTokens.Color.textPrimary)
                            Spacer()
                            if appTheme == opt.id {
                                Image(systemName: "checkmark").foregroundColor(DesignTokens.Color.accent)
                            }
                        }
                    }
                }
            } header: {
                Text("Appearance")
            } footer: {
                Text("Choose how TimeSense looks. System follows your device setting.")
            }
        }
        .navigationTitle("Appearance")
        .navigationBarTitleDisplayMode(.inline)
    }
}

// MARK: - Privacy & Consent

struct PrivacyConsentView: View {
    var body: some View {
        Form {
            Section {
                Text("TimeSense stores only what it needs to plan your day — your tasks, schedule, and preferences. Sensitive integrations (calendar, health) are opt-in, and raw audio is never stored unless you explicitly turn it on.")
                    .font(DesignTokens.Typography.subheadline)
                    .foregroundColor(DesignTokens.Color.textSecondary)
            }
            Section("Your data") {
                Label("Data is scoped to your account only", systemImage: "lock.fill")
                Label("Integration tokens are encrypted at rest", systemImage: "key.fill")
                Label("Delete your account anytime (Settings ▸ Delete My Data)", systemImage: "trash")
            }
        }
        .navigationTitle("Privacy & Consent")
        .navigationBarTitleDisplayMode(.inline)
    }
}

// MARK: - Calendar

struct CalendarSettingsView: View {
    var body: some View {
        Form {
            Section {
                Label("No calendar connected", systemImage: "calendar.badge.exclamationmark")
                    .foregroundColor(DesignTokens.Color.textSecondary)
            } footer: {
                Text("Calendar sync (Google / Apple) reads your events so TimeSense can plan around them. Connect it from the TimeSense web app for now — in-app connection is coming soon.")
            }
        }
        .navigationTitle("Calendar")
        .navigationBarTitleDisplayMode(.inline)
    }
}

// MARK: - About

struct AboutSettingsView: View {
    var body: some View {
        Form {
            Section {
                VStack(spacing: DesignTokens.Spacing.sm) {
                    Image(systemName: "clock")
                        .font(.system(size: 40, weight: .semibold))
                        .foregroundColor(DesignTokens.Color.accent)
                    Text("TimeSense")
                        .font(DesignTokens.Typography.title2)
                        .foregroundColor(DesignTokens.Color.textPrimary)
                    Text("Your personal time assistant")
                        .font(DesignTokens.Typography.footnote)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, DesignTokens.Spacing.md)
            }
            Section {
                LabeledContent("Version", value: "0.1.0")
                LabeledContent("Made for", value: "iOS")
            } footer: {
                Text("Don't make managing your day another job.")
            }
        }
        .navigationTitle("About")
        .navigationBarTitleDisplayMode(.inline)
    }
}
