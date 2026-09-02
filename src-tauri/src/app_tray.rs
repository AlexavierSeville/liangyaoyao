use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::TrayIconBuilder,
    App,
};

const QUIT_MENU_ID: &str = "tray-quit";
const SETTINGS_MENU_ID: &str = "tray-settings";

pub fn setup(app: &mut App) -> tauri::Result<()> {
    let settings = MenuItem::with_id(app, SETTINGS_MENU_ID, "控制面板", true, None::<&str>)?;
    let separator = PredefinedMenuItem::separator(app)?;
    let quit = MenuItem::with_id(app, QUIT_MENU_ID, "退出", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&settings, &separator, &quit])?;
    let mut tray = TrayIconBuilder::with_id("desktop-pet-tray")
        .menu(&menu)
        .show_menu_on_left_click(false)
        .tooltip("Codex Penguin")
        .on_menu_event(|app, event| match event.id.as_ref() {
            SETTINGS_MENU_ID => {
                if let Err(error) = crate::app_control::open_settings(app.clone()) {
                    eprintln!("Unable to open settings window: {error}");
                }
            }
            QUIT_MENU_ID => app.exit(0),
            _ => {}
        });

    if let Some(icon) = app.default_window_icon() {
        tray = tray.icon(icon.clone());
    }

    tray.build(app)?;
    Ok(())
}
