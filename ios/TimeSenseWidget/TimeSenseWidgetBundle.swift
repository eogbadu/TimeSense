import WidgetKit
import SwiftUI

@main
struct TimeSenseWidgetBundle: WidgetBundle {
    var body: some Widget {
        UsableTimeWidget()
        NextEventWidget()
        BestNextActionWidget()
    }
}
