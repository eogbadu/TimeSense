// swift-tools-version: 5.10
// This file exists solely to declare SPM dependencies for Xcode to resolve.
// Add packages via Xcode → File → Add Package Dependencies (or edit the xcodeproj directly).
//
// Required packages (add via Xcode):
//   - Firebase iOS SDK: https://github.com/firebase/firebase-ios-sdk (~> 11.0)
//     Products needed: FirebaseAuth, FirebaseAnalytics
//   - Google Sign-In: https://github.com/google/GoogleSignIn-iOS (~> 7.0)
//     Products needed: GoogleSignIn
//
// After adding:
//   1. Download GoogleService-Info.plist from Firebase Console → add to ios/TimeSense/
//   2. Register reverse client ID from GoogleService-Info.plist as a URL scheme in Info.plist
//   3. Enable Sign In with Apple capability in Xcode signing settings

import PackageDescription

let package = Package(
    name: "TimeSense",
    platforms: [.iOS(.v17)],
    dependencies: []
)
