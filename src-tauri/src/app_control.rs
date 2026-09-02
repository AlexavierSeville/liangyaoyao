use tauri::{AppHandle, Manager};

const SETTINGS_WINDOW_LABEL: &str = "settings";

#[tauri::command]
pub fn quit_app(app: AppHandle) {
    app.exit(0);
}

#[tauri::command]
pub fn open_settings(app: AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window(SETTINGS_WINDOW_LABEL) {
        window.unminimize().map_err(|error| error.to_string())?;
        window.show().map_err(|error| error.to_string())?;
        window.set_focus().map_err(|error| error.to_string())?;
        return Ok(());
    }

    tauri::WebviewWindowBuilder::new(
        &app,
        SETTINGS_WINDOW_LABEL,
        tauri::WebviewUrl::App("index.html?window=settings".into()),
    )
    .title("桌宠控制面板")
    .inner_size(460.0, 390.0)
    .min_inner_size(460.0, 390.0)
    .max_inner_size(460.0, 390.0)
    .visible(false)
    .transparent(false)
    .resizable(false)
    .center()
    .build()
    .map_err(|error| error.to_string())
    .and_then(|window| {
        window.show().map_err(|error| error.to_string())?;
        window.set_focus().map_err(|error| error.to_string())?;
        Ok(())
    })
}
