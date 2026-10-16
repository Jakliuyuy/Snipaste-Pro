#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wchar.h>
#include <stdio.h>

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    (void)hInstance; (void)hPrevInstance; (void)lpCmdLine; (void)nCmdShow;

    WCHAR appDir[MAX_PATH];
    DWORD len = GetModuleFileNameW(NULL, appDir, MAX_PATH);
    if (len == 0 || len >= MAX_PATH) {
        MessageBoxW(NULL, L"获取程序运行路径失败！", L"Snipaste 启动错误", MB_ICONERROR);
        return 1;
    }

    WCHAR *lastBackslash = wcsrchr(appDir, L'\\');
    if (lastBackslash) {
        *lastBackslash = L'\0';
    }

    WCHAR officialExe[MAX_PATH];
    swprintf(officialExe, MAX_PATH, L"%ls\\Snipaste.exe", appDir);

    WCHAR pythonExe[MAX_PATH];
    swprintf(pythonExe, MAX_PATH, L"%ls\\runtime\\pythonw.exe", appDir);

    WCHAR transScript[MAX_PATH];
    swprintf(transScript, MAX_PATH, L"%ls\\translator\\main.py", appDir);

    if (GetFileAttributesW(officialExe) == INVALID_FILE_ATTRIBUTES) {
        WCHAR errMsg[1024];
        swprintf(errMsg, 1024,
            L"未在当前目录下找到官方 Snipaste.exe：\n%ls\n\n"
            L"请确保 Snipaste.exe 处于当前文件夹内。", officialExe);
        MessageBoxW(NULL, errMsg, L"Snipaste 启动提示", MB_ICONWARNING);
        return 1;
    }

    STARTUPINFOW si;
    PROCESS_INFORMATION piOfficial;
    PROCESS_INFORMATION piTrans;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);

    // 1. 启动官方正版 Snipaste.exe
    if (CreateProcessW(officialExe, officialExe, NULL, NULL, FALSE, 0, NULL, appDir, &si, &piOfficial)) {
        CloseHandle(piOfficial.hProcess);
        CloseHandle(piOfficial.hThread);
    } else {
        DWORD err = GetLastError();
        WCHAR failMsg[512];
        swprintf(failMsg, 512, L"启动官方 Snipaste.exe 失败 (错误代码: %lu)", err);
        MessageBoxW(NULL, failMsg, L"启动错误", MB_ICONERROR);
        return 1;
    }

    // 2. 启动智能实时翻译伴侣
    if (GetFileAttributesW(pythonExe) != INVALID_FILE_ATTRIBUTES && GetFileAttributesW(transScript) != INVALID_FILE_ATTRIBUTES) {
        WCHAR transCmd[MAX_PATH * 3];
        swprintf(transCmd, MAX_PATH * 3, L"\"%ls\" \"%ls\"", pythonExe, transScript);
        si.dwFlags = STARTF_USESHOWWINDOW;
        si.wShowWindow = SW_HIDE;
        if (CreateProcessW(pythonExe, transCmd, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, appDir, &si, &piTrans)) {
            CloseHandle(piTrans.hProcess);
            CloseHandle(piTrans.hThread);
        }
    }

    return 0;
}
