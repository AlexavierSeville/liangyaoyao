mod app_control;
mod app_tray;

#[cfg(windows)]
mod pet_drag {
    use serde::Serialize;
    use std::{
        ffi::c_void,
        sync::{
            atomic::{AtomicBool, Ordering},
            Arc, Mutex,
        },
        thread,
        time::Duration,
    };
    use tauri::{Emitter, State, WebviewWindow};

    const VK_LBUTTON: i32 = 0x01;
    const SWP_NOSIZE: u32 = 0x0001;
    const SWP_NOZORDER: u32 = 0x0004;
    const SWP_NOACTIVATE: u32 = 0x0010;
    const SWP_ASYNCWINDOWPOS: u32 = 0x4000;
    const DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2: isize = -4;
    const DRAG_POLL_INTERVAL: Duration = Duration::from_millis(8);

    #[repr(C)]
    #[derive(Clone, Copy, Default)]
    struct Point {
        x: i32,
        y: i32,
    }

    #[repr(C)]
    #[derive(Clone, Copy, Default)]
    struct Rect {
        left: i32,
        top: i32,
        right: i32,
        bottom: i32,
    }

    #[link(name = "user32")]
    extern "system" {
        #[link_name = "GetCursorPos"]
        fn get_cursor_pos(point: *mut Point) -> i32;
        #[link_name = "GetWindowRect"]
        fn get_window_rect(hwnd: *mut c_void, rect: *mut Rect) -> i32;
        #[link_name = "GetAsyncKeyState"]
        fn get_async_key_state(key: i32) -> i16;
        #[link_name = "SetWindowPos"]
        fn set_window_pos(
            hwnd: *mut c_void,
            insert_after: *mut c_void,
            x: i32,
            y: i32,
            width: i32,
            height: i32,
            flags: u32,
        ) -> i32;
        #[link_name = "SetThreadDpiAwarenessContext"]
        fn set_thread_dpi_awareness_context(context: isize) -> isize;
    }

    #[derive(Default)]
    pub struct DragController {
        active: Mutex<Option<Arc<AtomicBool>>>,
    }

    #[derive(Clone, Serialize)]
    #[serde(rename_all = "camelCase")]
    struct DragDelta {
        dx: i32,
        dy: i32,
    }

    #[tauri::command]
    pub fn start_pet_drag(
        window: WebviewWindow,
        controller: State<'_, DragController>,
    ) -> Result<(), String> {
        let mut active = controller
            .active
            .lock()
            .map_err(|_| "drag controller lock is poisoned".to_string())?;
        if active
            .as_ref()
            .is_some_and(|token| token.load(Ordering::Relaxed))
        {
            return Ok(());
        }

        let hwnd = window
            .hwnd()
            .map_err(|error| error.to_string())?
            .0 as isize;
        let mut start_cursor = Point::default();
        let mut start_window = Rect::default();
        unsafe {
            if get_cursor_pos(&mut start_cursor) == 0 {
                return Err("unable to read the cursor position".to_string());
            }
            if get_window_rect(hwnd as *mut c_void, &mut start_window) == 0 {
                return Err("unable to read the pet window position".to_string());
            }
        }

        let token = Arc::new(AtomicBool::new(true));
        *active = Some(token.clone());
        drop(active);

        thread::spawn(move || {
            unsafe {
                set_thread_dpi_awareness_context(
                    DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2,
                );
            }
            let mut last_cursor = start_cursor;
            while token.load(Ordering::Relaxed) && left_button_is_pressed() {
                let mut cursor = Point::default();
                if unsafe { get_cursor_pos(&mut cursor) } == 0 {
                    break;
                }

                let dx = cursor.x - last_cursor.x;
                let dy = cursor.y - last_cursor.y;
                if dx != 0 || dy != 0 {
                    let x = start_window.left + (cursor.x - start_cursor.x);
                    let y = start_window.top + (cursor.y - start_cursor.y);
                    unsafe {
                        set_window_pos(
                            hwnd as *mut c_void,
                            std::ptr::null_mut(),
                            x,
                            y,
                            0,
                            0,
                            SWP_NOSIZE
                                | SWP_NOZORDER
                                | SWP_NOACTIVATE
                                | SWP_ASYNCWINDOWPOS,
                        );
                    }
                    let _ = window.emit("pet-drag-move", DragDelta { dx, dy });
                    last_cursor = cursor;
                }
                thread::sleep(DRAG_POLL_INTERVAL);
            }

            token.store(false, Ordering::Relaxed);
            let _ = window.emit("pet-drag-end", ());
        });

        Ok(())
    }

    #[tauri::command]
    pub fn stop_pet_drag(controller: State<'_, DragController>) -> Result<(), String> {
        let active = controller
            .active
            .lock()
            .map_err(|_| "drag controller lock is poisoned".to_string())?;
        if let Some(token) = active.as_ref() {
            token.store(false, Ordering::Relaxed);
        }
        Ok(())
    }

    fn left_button_is_pressed() -> bool {
        unsafe { get_async_key_state(VK_LBUTTON) < 0 }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let builder = tauri::Builder::default().setup(|app| {
        app_tray::setup(app)?;
        Ok(())
    });

    #[cfg(windows)]
    let builder = builder
        .manage(pet_drag::DragController::default())
        .invoke_handler(tauri::generate_handler![
            app_control::quit_app,
            pet_drag::start_pet_drag,
            pet_drag::stop_pet_drag
        ]);

    #[cfg(not(windows))]
    let builder = builder.invoke_handler(tauri::generate_handler![app_control::quit_app]);

    builder
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
