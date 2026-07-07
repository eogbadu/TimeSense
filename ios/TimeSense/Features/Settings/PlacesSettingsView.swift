import CoreLocation
import SwiftUI

struct PlacesSettingsView: View {
    @ObservedObject private var location = LocationService.shared

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                Text("TimeSense uses your location to recommend the right task for where you are. With Always access, it can notify you when you arrive at or leave a saved place. Raw location is never stored.")
                    .font(DesignTokens.Typography.subheadline)
                    .foregroundColor(DesignTokens.Color.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(DesignTokens.Spacing.lg)
                    .background(RoundedRectangle(cornerRadius: DesignTokens.Radius.xl, style: .continuous).fill(DesignTokens.Color.accent.opacity(0.10)))

                VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
                    HStack {
                        Text("Location access").font(DesignTokens.Typography.body).foregroundColor(DesignTokens.Color.textPrimary)
                        Spacer()
                        Text(statusLabel).font(DesignTokens.Typography.footnote.weight(.semibold)).foregroundColor(statusColor)
                    }

                    switch location.authorizationStatus {
                    case .notDetermined:
                        primaryButton("Enable location") { location.requestPermission() }
                    case .authorizedWhenInUse:
                        Text("Arrival alerts need **Always** access. iOS won't show that prompt in the app — set it in Settings ▸ Location ▸ Always.")
                            .font(DesignTokens.Typography.footnote)
                            .foregroundColor(DesignTokens.Color.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                        primaryButton("Open iOS Settings") { location.openAppSettings() }
                    case .denied, .restricted:
                        Text("Location is off. Turn it on in Settings ▸ Location.")
                            .font(DesignTokens.Typography.footnote)
                            .foregroundColor(DesignTokens.Color.textSecondary)
                        primaryButton("Open iOS Settings") { location.openAppSettings() }
                    default:
                        Text("You're all set — arrival alerts are on.")
                            .font(DesignTokens.Typography.footnote)
                            .foregroundColor(DesignTokens.Color.textSecondary)
                    }
                }
                .padding(DesignTokens.Spacing.lg)
                .cardStyle()

                Text("Saved places")
                    .font(DesignTokens.Typography.headline)
                    .foregroundColor(DesignTokens.Color.accent)
                    .padding(.horizontal, DesignTokens.Spacing.xs)

                if location.places.isEmpty {
                    Text("No places yet. Save where you are now as Home or Work to get arrival alerts.")
                        .font(DesignTokens.Typography.subheadline)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(DesignTokens.Spacing.lg)
                        .cardStyle()
                } else {
                    VStack(spacing: 0) {
                        ForEach(Array(location.places.enumerated()), id: \.element.id) { idx, place in
                            HStack(spacing: DesignTokens.Spacing.md) {
                                Image(systemName: place.name.lowercased() == "home" ? "house.fill" : "mappin.circle.fill")
                                    .font(.title3).foregroundColor(DesignTokens.Color.accent).frame(width: 28)
                                Text(place.name).font(DesignTokens.Typography.body).foregroundColor(DesignTokens.Color.textPrimary)
                                Spacer()
                                Button(role: .destructive) { location.removePlace(place) } label: {
                                    Image(systemName: "trash").foregroundColor(DesignTokens.Color.destructive)
                                }
                            }
                            .padding(DesignTokens.Spacing.md)
                            if idx < location.places.count - 1 { Divider().padding(.leading, 52) }
                        }
                    }
                    .cardStyle()
                }

                if location.isAuthorized {
                    HStack(spacing: DesignTokens.Spacing.md) {
                        savePlaceButton("Home", icon: "house.fill")
                        savePlaceButton("Work", icon: "briefcase.fill")
                    }
                    .disabled(location.currentLocation == nil)
                    .opacity(location.currentLocation == nil ? 0.5 : 1)
                    if location.currentLocation == nil {
                        Text("Getting your current location…")
                            .font(DesignTokens.Typography.footnote)
                            .foregroundColor(DesignTokens.Color.textSecondary)
                    }
                }
            }
            .padding(.horizontal, DesignTokens.Spacing.lg)
            .padding(.top, DesignTokens.Spacing.sm)
            .padding(.bottom, DesignTokens.Spacing.xxl)
        }
        .background(DesignTokens.Color.background)
        .navigationTitle("Location & Places")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear { location.requestOneTimeLocation() }
    }

    private func savePlaceButton(_ name: String, icon: String) -> some View {
        Button { location.savePlace(named: name) } label: {
            Label("Save current as \(name)", systemImage: icon)
                .font(DesignTokens.Typography.footnote.weight(.semibold))
                .foregroundColor(DesignTokens.Color.accent)
                .frame(maxWidth: .infinity)
                .padding(.vertical, DesignTokens.Spacing.md)
                .background(Capsule().stroke(DesignTokens.Color.accent, lineWidth: 1))
        }
        .buttonStyle(.plain)
    }

    private var statusLabel: String {
        switch location.authorizationStatus {
        case .authorizedAlways: return "Always"
        case .authorizedWhenInUse: return "While Using"
        case .denied, .restricted: return "Off"
        default: return "Not set"
        }
    }
    private var statusColor: Color {
        location.authorizationStatus == .authorizedAlways ? .green : DesignTokens.Color.textSecondary
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
}
