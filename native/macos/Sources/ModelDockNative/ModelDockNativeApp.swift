import AppKit
import SwiftUI

@main
struct ModelDockNativeApp: App {
    @StateObject private var model = AppModel()

    var body: some Scene {
        WindowGroup("ModelDock", id: "main") {
            ContentView().environmentObject(model)
        }
        .defaultSize(width: 1280, height: 800)
        .windowResizability(.contentMinSize)
        .commands {
            CommandGroup(replacing: .newItem) { }
            CommandMenu("ModelDock") {
                Button("刷新全部状态") { model.refresh(showBusy: true) }.keyboardShortcut("r")
            }
        }

        MenuBarExtra {
            MenuBarContent().environmentObject(model)
        } label: {
            Image(nsImage: menuBarImage())
        }
        .menuBarExtraStyle(.menu)
    }

    private func menuBarImage() -> NSImage {
        let resources = Bundle.main.resourceURL
        let paths = [
            resources?.appending(path: "menu_bar_iconTemplate.png"),
            resources?.appending(path: "menu_bar_iconTemplate@2x.png"),
        ].compactMap { $0 }

        let image = NSImage(size: NSSize(width: 18, height: 18))
        for path in paths {
            guard let data = try? Data(contentsOf: path),
                  let bitmap = NSBitmapImageRep(data: data) else { continue }
            // Keep the native 18 pt / 36 px Retina template untouched. Any
            // resizing or alpha manipulation here makes a menu extra blurry.
            bitmap.size = NSSize(width: 18, height: 18)
            image.addRepresentation(bitmap)
        }
        if image.representations.isEmpty {
            return NSImage(systemSymbolName: "shippingbox", accessibilityDescription: "ModelDock")!
        }
        image.isTemplate = true
        return image
    }
}

private struct MenuBarContent: View {
    @Environment(\.openWindow) private var openWindow
    @EnvironmentObject private var model: AppModel

    var body: some View {
        Button("显示 ModelDock") {
            openWindow(id: "main")
            NSApp.activate(ignoringOtherApps: true)
        }
        Divider()
        Button("刷新状态") { model.refresh() }
        Button("启动 / 重启网关") {
            model.perform("gateway_action", payload: ["action": "restart"], as: ActionResult.self)
        }
        Divider()
        Button("退出") { NSApp.terminate(nil) }
    }
}
