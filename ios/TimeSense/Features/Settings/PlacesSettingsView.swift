import CoreLocation
import SwiftUI

struct PlacesSettingsView: View {
    @ObservedObject private var location = LocationService.shared
    @State private var newPlaceName = ""

    private let quickNames = ["Home", "Work", "Gym", "School", "Errands"]
    private var atCap: Bool { location.places.count >= 20 }
    private var canSave: Bool {
        !newPlaceName.trimmingCharacters(in: .whitespaces).isEmpty
            && location.currentLocation != nil && !atCap
    }

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
                                Image(systemName: placeIcon(place.name))
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
                    VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
                        Text("Add this location")
                            .font(DesignTokens.Typography.headline)
                            .foregroundColor(DesignTokens.Color.textPrimary)

                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: DesignTokens.Spacing.sm) {
                                ForEach(quickNames, id: \.self) { name in
                                    Button { newPlaceName = name } label: {
                                        Text(name)
                                            .font(DesignTokens.Typography.footnote.weight(.medium))
                                            .foregroundColor(DesignTokens.Color.accent)
                                            .padding(.horizontal, DesignTokens.Spacing.md)
                                            .padding(.vertical, DesignTokens.Spacing.sm)
                                            .background(Capsule().stroke(DesignTokens.Color.accent.opacity(0.4), lineWidth: 1))
                                    }
                                    .buttonStyle(.plain)
                                }
                            }
                            .padding(.horizontal, 2)
                        }

                        HStack(spacing: DesignTokens.Spacing.sm) {
                            TextField("Name (e.g. Gym)", text: $newPlaceName)
                                .font(DesignTokens.Typography.body)
                                .padding(DesignTokens.Spacing.md)
                                .background(RoundedRectangle(cornerRadius: DesignTokens.Radius.lg, style: .continuous).fill(DesignTokens.Color.surface))
                                .overlay(RoundedRectangle(cornerRadius: DesignTokens.Radius.lg, style: .continuous).stroke(DesignTokens.Color.textSecondary.opacity(0.15), lineWidth: 1))
                            Button {
                                location.savePlace(named: newPlaceName.trimmingCharacters(in: .whitespaces))
                                newPlaceName = ""
                            } label: {
                                Text("Save here")
                                    .font(DesignTokens.Typography.headline)
                                    .foregroundColor(.white)
                                    .padding(.horizontal, DesignTokens.Spacing.lg)
                                    .padding(.vertical, DesignTokens.Spacing.md)
                                    .background(Capsule().fill(DesignTokens.Color.accent))
                            }
                            .disabled(!canSave)
                            .opacity(canSave ? 1 : 0.5)
                        }

                        if location.currentLocation == nil {
                            Text("Getting your current location…")
                                .font(DesignTokens.Typography.footnote)
                                .foregroundColor(DesignTokens.Color.textSecondary)
                        } else if atCap {
                            Text("You've reached the maximum of 20 saved places. Remove one to add another.")
                                .font(DesignTokens.Typography.footnote)
                                .foregroundColor(DesignTokens.Color.textSecondary)
                        }
                    }
                    .padding(DesignTokens.Spacing.lg)
                    .cardStyle()
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

    private func placeIcon(_ name: String) -> String {
        switch name.lowercased() {
        case "home": return "house.fill"
        case "work", "office": return "briefcase.fill"
        case "gym": return "figure.run"
        case "school": return "graduationcap.fill"
        case "errands": return "cart.fill"
        default: return "mappin.circle.fill"
        }
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
