import SwiftUI
import UIKit

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

    private let basicFeatures = [
        "Task capture & organization", "Daily task list", "Basic recommendations", "1 integration",
    ]
    private let premiumFeatures = [
        "AI best-next-action recommendations", "Calendar, health & more integrations",
        "Weekly AI insights & patterns", "Proactive notifications", "Unlimited integrations",
    ]

    var body: some View {
        ScrollView {
            VStack(spacing: DesignTokens.Spacing.lg) {
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Current Plan")
                            .font(DesignTokens.Typography.footnote)
                            .foregroundColor(DesignTokens.Color.textSecondary)
                        Text(isPremium ? "Premium" : "Basic (Free)")
                            .font(DesignTokens.Typography.title2)
                            .foregroundColor(DesignTokens.Color.textPrimary)
                    }
                    Spacer()
                    Image(systemName: isPremium ? "crown.fill" : "leaf.fill")
                        .font(.title2)
                        .foregroundColor(isPremium ? DesignTokens.Color.accent : .green)
                }
                .padding(DesignTokens.Spacing.lg)
                .cardStyle()

                VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
                    Text("Basic includes")
                        .font(DesignTokens.Typography.headline)
                        .foregroundColor(DesignTokens.Color.accent)
                    ForEach(basicFeatures, id: \.self) { f in
                        HStack(spacing: DesignTokens.Spacing.md) {
                            Image(systemName: "checkmark").foregroundColor(.green).font(.footnote.weight(.bold))
                            Text(f).font(DesignTokens.Typography.callout).foregroundColor(DesignTokens.Color.textPrimary)
                            Spacer(minLength: 0)
                        }
                    }
                }
                .padding(DesignTokens.Spacing.lg)
                .cardStyle()

                VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
                    Text("Premium unlocks")
                        .font(DesignTokens.Typography.headline)
                        .foregroundColor(.white)
                    ForEach(premiumFeatures, id: \.self) { f in
                        HStack(spacing: DesignTokens.Spacing.md) {
                            Image(systemName: "sparkles").foregroundColor(.yellow).font(.footnote)
                            Text(f).font(DesignTokens.Typography.callout).foregroundColor(.white)
                            Spacer(minLength: 0)
                        }
                    }
                }
                .padding(DesignTokens.Spacing.lg)
                .background(RoundedRectangle(cornerRadius: DesignTokens.Radius.xl, style: .continuous).fill(DesignTokens.Color.accent))

                if !isPremium {
                    Button {
                        /* StoreKit purchase — follow-up */
                    } label: {
                        Text("Upgrade to Premium")
                            .font(DesignTokens.Typography.headline)
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, DesignTokens.Spacing.md)
                            .background(Capsule().fill(DesignTokens.Color.accent))
                    }
                    Text("Plans managed in the App Store")
                        .font(DesignTokens.Typography.footnote)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                }
            }
            .padding(.horizontal, DesignTokens.Spacing.lg)
            .padding(.top, DesignTokens.Spacing.sm)
            .padding(.bottom, DesignTokens.Spacing.xxl)
        }
        .background(DesignTokens.Color.background)
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

// MARK: - Working Hours

struct WorkingHoursSettingsView: View {
    @State private var start = 8
    @State private var end = 21
    @State private var loaded = false
    @State private var saving = false
    @State private var saved = false

    private struct Me: Decodable {
        let preferences: Prefs?
        struct Prefs: Decodable { let work_start_hour: Int; let work_end_hour: Int }
    }
    private struct Update: Encodable { let work_start_hour: Int; let work_end_hour: Int }
    private struct Resp: Decodable { let work_start_hour: Int }

    private func label(_ h: Int) -> String {
        let period = h < 12 ? "AM" : "PM"
        let hour12 = h % 12 == 0 ? 12 : h % 12
        return "\(hour12):00 \(period)"
    }

    private let days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    @State private var selectedDays: Set<String> = ["Mon", "Tue", "Wed", "Thu", "Fri"]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                Text("TimeSense uses your working hours to decide when tasks are appropriate and to protect your personal time.")
                    .font(DesignTokens.Typography.subheadline)
                    .foregroundColor(DesignTokens.Color.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(DesignTokens.Spacing.lg)
                    .background(RoundedRectangle(cornerRadius: DesignTokens.Radius.xl, style: .continuous).fill(DesignTokens.Color.accent.opacity(0.10)))

                VStack(spacing: 0) {
                    hourRow(title: "Start", selection: $start, range: Array(0..<23))
                    Divider().padding(.leading, DesignTokens.Spacing.md)
                    hourRow(title: "End", selection: $end, range: Array(1..<24))
                    Divider().padding(.leading, DesignTokens.Spacing.md)
                    VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                        Text("Repeat")
                            .font(DesignTokens.Typography.headline)
                            .foregroundColor(DesignTokens.Color.textPrimary)
                        HStack(spacing: DesignTokens.Spacing.xs) {
                            ForEach(days, id: \.self) { day in
                                let on = selectedDays.contains(day)
                                Button {
                                    if on { selectedDays.remove(day) } else { selectedDays.insert(day) }
                                } label: {
                                    Text(day)
                                        .font(DesignTokens.Typography.caption.weight(.semibold))
                                        .foregroundColor(on ? .white : DesignTokens.Color.textSecondary)
                                        .frame(maxWidth: .infinity)
                                        .frame(height: 40)
                                        .background(Circle().fill(on ? DesignTokens.Color.accent : DesignTokens.Color.surface))
                                        .overlay(Circle().stroke(DesignTokens.Color.textSecondary.opacity(0.2), lineWidth: on ? 0 : 1))
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }
                    .padding(DesignTokens.Spacing.md)
                }
                .cardStyle()

                if end <= start {
                    Text("End time must be after start time.")
                        .font(DesignTokens.Typography.footnote)
                        .foregroundColor(DesignTokens.Color.destructive)
                        .padding(.horizontal, DesignTokens.Spacing.xs)
                }

                Button {
                    Task { await save() }
                } label: {
                    HStack {
                        if saving { ProgressView().tint(.white) }
                        Text(saved ? "Saved" : "Save").font(DesignTokens.Typography.headline)
                    }
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, DesignTokens.Spacing.md)
                    .background(Capsule().fill(DesignTokens.Color.accent))
                }
                .disabled(saving || end <= start)
                .opacity(end <= start ? 0.5 : 1)
                .padding(.top, DesignTokens.Spacing.sm)
            }
            .padding(.horizontal, DesignTokens.Spacing.lg)
            .padding(.top, DesignTokens.Spacing.sm)
            .padding(.bottom, DesignTokens.Spacing.xxl)
        }
        .background(DesignTokens.Color.background)
        .navigationTitle("Working Hours")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
        .onChange(of: start) { _, _ in saved = false }
        .onChange(of: end) { _, _ in saved = false }
    }

    private func hourRow(title: String, selection: Binding<Int>, range: [Int]) -> some View {
        HStack {
            Text(title)
                .font(DesignTokens.Typography.body)
                .foregroundColor(DesignTokens.Color.textPrimary)
            Spacer()
            Picker(title, selection: selection) {
                ForEach(range, id: \.self) { h in Text(label(h)).tag(h) }
            }
            .labelsHidden()
            .tint(DesignTokens.Color.accent)
        }
        .padding(DesignTokens.Spacing.md)
    }

    private func load() async {
        guard !loaded else { return }
        loaded = true
        if let me: Me = try? await APIClient.shared.get("/api/v1/users/me"), let p = me.preferences {
            start = p.work_start_hour
            end = p.work_end_hour
        }
    }

    private func save() async {
        saving = true
        defer { saving = false }
        let _: Resp? = try? await APIClient.shared.patch(
            "/api/v1/users/me/preferences", body: Update(work_start_hour: start, work_end_hour: end)
        )
        saved = true
    }
}

// MARK: - Privacy & Consent

struct PrivacyConsentView: View {
    @EnvironmentObject private var authService: AuthService
    @ObservedObject private var location = LocationService.shared
    @State private var showDeleteConfirm = false
    @State private var deleting = false
    @State private var showExportSoon = false

    private struct Signal {
        let icon: String; let color: Color; let name: String; let detail: String
        let status: String; let statusColor: Color
    }
    private var locationStatus: (String, Color) {
        switch location.authorizationStatus {
        case .authorizedAlways: return ("Always", .green)
        case .authorizedWhenInUse: return ("While Using", .green)
        default: return ("Off", DesignTokens.Color.textSecondary)
        }
    }
    private var signals: [Signal] {
        [
            Signal(icon: "calendar", color: .blue, name: "Calendar", detail: "See events and availability", status: "Off", statusColor: DesignTokens.Color.textSecondary),
            Signal(icon: "heart.fill", color: .red, name: "Health / Wake Signals", detail: "Energy & routine estimation", status: "Off", statusColor: DesignTokens.Color.textSecondary),
            Signal(icon: "location.fill", color: .blue, name: "Location", detail: "Commute & errand timing", status: locationStatus.0, statusColor: locationStatus.1),
            Signal(icon: "mic.fill", color: DesignTokens.Color.accent, name: "Audio (Voice Capture)", detail: "Speech is processed securely", status: "Disabled", statusColor: DesignTokens.Color.textSecondary),
        ]
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                banner("TimeSense only uses the data needed to plan your day. You're in control.")

                sectionHeader("Connected signals")
                VStack(spacing: 0) {
                    ForEach(Array(signals.enumerated()), id: \.offset) { idx, s in
                        HStack(spacing: DesignTokens.Spacing.md) {
                            Image(systemName: s.icon).font(.title3).foregroundColor(s.color).frame(width: 30)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(s.name).font(DesignTokens.Typography.callout.weight(.semibold)).foregroundColor(DesignTokens.Color.textPrimary)
                                Text(s.detail).font(DesignTokens.Typography.footnote).foregroundColor(DesignTokens.Color.textSecondary)
                            }
                            Spacer(minLength: DesignTokens.Spacing.sm)
                            Text(s.status).font(DesignTokens.Typography.footnote.weight(.semibold)).foregroundColor(s.statusColor)
                        }
                        .padding(DesignTokens.Spacing.md)
                        if idx < signals.count - 1 { Divider().padding(.leading, 54) }
                    }
                }
                .cardStyle()

                sectionHeader("Data controls")
                VStack(spacing: 0) {
                    controlRow(icon: "trash", title: "Delete my data", role: .destructive) { showDeleteConfirm = true }
                    Divider().padding(.leading, 54)
                    controlRow(icon: "square.and.arrow.up", title: "Export my data") { showExportSoon = true }
                }
                .cardStyle()

                HStack(alignment: .top, spacing: DesignTokens.Spacing.md) {
                    Image(systemName: "checkmark.shield.fill").foregroundColor(DesignTokens.Color.textSecondary)
                    Text("Your data is encrypted and never sold. Learn more in our Privacy Policy.")
                        .font(DesignTokens.Typography.footnote)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                    Spacer(minLength: 0)
                }
                .padding(DesignTokens.Spacing.md)
                .background(RoundedRectangle(cornerRadius: DesignTokens.Radius.lg, style: .continuous).fill(DesignTokens.Color.textSecondary.opacity(0.08)))

                if deleting { ProgressView().frame(maxWidth: .infinity) }
            }
            .padding(.horizontal, DesignTokens.Spacing.lg)
            .padding(.top, DesignTokens.Spacing.sm)
            .padding(.bottom, DesignTokens.Spacing.xxl)
        }
        .background(DesignTokens.Color.background)
        .navigationTitle("Privacy & Consent")
        .navigationBarTitleDisplayMode(.inline)
        .alert("Delete your account?", isPresented: $showDeleteConfirm) {
            Button("Cancel", role: .cancel) {}
            Button("Delete everything", role: .destructive) { Task { await deleteAccount() } }
        } message: {
            Text("This permanently erases your account and all your data. This cannot be undone.")
        }
        .alert("Data export is coming soon", isPresented: $showExportSoon) {
            Button("OK", role: .cancel) {}
        } message: {
            Text("You'll be able to download a full copy of your data from here shortly.")
        }
    }

    private func sectionHeader(_ text: String) -> some View {
        Text(text).font(DesignTokens.Typography.headline).foregroundColor(DesignTokens.Color.accent)
            .padding(.horizontal, DesignTokens.Spacing.xs)
    }

    private func banner(_ text: String) -> some View {
        Text(text)
            .font(DesignTokens.Typography.subheadline)
            .foregroundColor(DesignTokens.Color.textPrimary)
            .fixedSize(horizontal: false, vertical: true)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(DesignTokens.Spacing.lg)
            .background(RoundedRectangle(cornerRadius: DesignTokens.Radius.xl, style: .continuous).fill(DesignTokens.Color.accent.opacity(0.10)))
    }

    private func controlRow(icon: String, title: String, role: ButtonRole? = nil, action: @escaping () -> Void) -> some View {
        Button(role: role, action: action) {
            HStack(spacing: DesignTokens.Spacing.md) {
                Image(systemName: icon).font(.title3)
                    .foregroundColor(role == .destructive ? DesignTokens.Color.destructive : DesignTokens.Color.textPrimary)
                    .frame(width: 28)
                Text(title).font(DesignTokens.Typography.body)
                    .foregroundColor(role == .destructive ? DesignTokens.Color.destructive : DesignTokens.Color.textPrimary)
                Spacer()
                Image(systemName: "chevron.right").font(.footnote).foregroundColor(DesignTokens.Color.textSecondary)
            }
            .padding(DesignTokens.Spacing.md)
        }
        .buttonStyle(.plain)
    }

    private func deleteAccount() async {
        deleting = true
        defer { deleting = false }
        try? await APIClient.shared.delete("/api/v1/privacy/account?confirm=true")
        authService.signOut()
    }
}

// MARK: - Calendar

struct CalendarSettingsView: View {
    @ObservedObject private var calendar = CalendarSyncService.shared

    var body: some View {
        ScrollView {
            VStack(spacing: DesignTokens.Spacing.lg) {
                ZStack {
                    RoundedRectangle(cornerRadius: DesignTokens.Radius.xl, style: .continuous)
                        .fill(DesignTokens.Color.accent.opacity(0.10))
                        .frame(width: 150, height: 150)
                    Image(systemName: calendar.status == .connected ? "calendar.badge.checkmark" : "calendar")
                        .font(.system(size: 64, weight: .regular))
                        .foregroundColor(DesignTokens.Color.accent)
                }
                .padding(.top, DesignTokens.Spacing.lg)

                VStack(spacing: DesignTokens.Spacing.sm) {
                    Text(calendar.status == .connected ? "Calendar connected" : "Connect your calendar")
                        .font(DesignTokens.Typography.title)
                        .foregroundColor(DesignTokens.Color.textPrimary)
                    Text("Let TimeSense avoid conflicts, find open focus blocks, and recommend the right task at the right time.")
                        .font(DesignTokens.Typography.callout)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, DesignTokens.Spacing.md)
                }

                switch calendar.status {
                case .connected:
                    if calendar.lastSyncedCount > 0 {
                        Text("\(calendar.lastSyncedCount) event\(calendar.lastSyncedCount == 1 ? "" : "s") in view")
                            .font(DesignTokens.Typography.footnote)
                            .foregroundColor(DesignTokens.Color.textSecondary)
                    }
                    primaryButton("Sync now") { Task { await calendar.syncIfAuthorized() } }
                    Button("Disconnect", role: .destructive) { Task { await calendar.disconnect() } }
                        .font(DesignTokens.Typography.subheadline)
                case .connecting:
                    ProgressView().padding(.vertical, DesignTokens.Spacing.md)
                case .denied:
                    Text("Calendar access is off. Enable it in Settings ▸ TimeSense ▸ Calendars.")
                        .font(DesignTokens.Typography.footnote)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                        .multilineTextAlignment(.center)
                    primaryButton("Open iOS Settings") {
                        if let url = URL(string: UIApplication.openSettingsURLString) { UIApplication.shared.open(url) }
                    }
                default:
                    primaryButton("Connect Apple Calendar") { Task { await calendar.connect() } }
                }

                VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                    Text("What TimeSense reads")
                        .font(DesignTokens.Typography.footnote)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                    VStack(spacing: 0) {
                        infoRow(icon: "clock", text: "Event times, to find your free blocks")
                        Divider().padding(.leading, 56)
                        infoRow(icon: "mappin.and.ellipse", text: "Locations, so it can tell you when to leave")
                    }
                    .cardStyle()
                }

                Text("Reads whatever calendars you've added to iOS — including Google. Event details never leave your control.")
                    .font(DesignTokens.Typography.caption)
                    .foregroundColor(DesignTokens.Color.textSecondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, DesignTokens.Spacing.md)
            }
            .padding(.horizontal, DesignTokens.Spacing.lg)
            .padding(.bottom, DesignTokens.Spacing.xxl)
        }
        .background(DesignTokens.Color.background)
        .navigationTitle("Calendar")
        .navigationBarTitleDisplayMode(.inline)
        .task { await calendar.syncIfAuthorized() }
    }

    private func primaryButton(_ title: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title)
                .font(DesignTokens.Typography.headline)
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, DesignTokens.Spacing.md)
                .background(Capsule().fill(DesignTokens.Color.accent))
        }
    }

    private func infoRow(icon: String, text: String) -> some View {
        HStack(spacing: DesignTokens.Spacing.md) {
            Image(systemName: icon).font(.title3).foregroundColor(DesignTokens.Color.accent).frame(width: 28)
            Text(text).font(DesignTokens.Typography.subheadline).foregroundColor(DesignTokens.Color.textPrimary)
            Spacer(minLength: 0)
        }
        .padding(DesignTokens.Spacing.md)
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
