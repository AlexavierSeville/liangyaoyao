use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    App,
};

const QUIT_MENU_ID: &str = "tray-quit";

pub fn setup(app: &mut App) -> tauri::Result<()> {
    let quit = MenuItem::with_id(app, QUIT_MENU_ID, "退出", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&quit])?;
    let mut tray = TrayIconBuilder::with_id("desktop-pet-tray")
        .menu(&menu)
        .show_menu_on_left_click(false)
        .tooltip("Codex Penguin")
        .on_menu_event(|app, event| {
            if event.id.as_ref() == QUIT_MENU_ID {
                app.exit(0);
            }
        });

    if let Some(icon) = app.default_window_icon() {
        tray = tray.icon(icon.clone());
    }

    tray.build(app)?;
    Ok(())
}
