package com.aiengine.sdk;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.provider.Settings;
import android.util.Log;
import android.view.View;
import android.webkit.PermissionRequest;
import android.view.ViewGroup;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.ConsoleMessage;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.view.WindowInsets;
import android.widget.FrameLayout;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public abstract class AiEngineWebShellActivity extends Activity {
    private static final String TAG = "AIEngineWebView";
    private static final int REQUEST_RECORD_AUDIO = 1001;
    private static final int REQUEST_BRIDGE_FILE_CHOOSER = 1002;
    private static final int REQUEST_WEB_FILE_CHOOSER = 1003;

    private AiEngineWebShellConfig webShellConfig;
    private WebView webView;
    private PermissionRequest pendingAudioPermissionRequest;
    private String[] pendingAudioPermissionResources;
    private ValueCallback<Uri[]> pendingWebFilePathCallback;
    private String pendingBridgeFileRequestId;
    private boolean recordAudioPermissionRequestInFlight;
    private boolean updateCheckStarted;

    protected abstract AiEngineWebShellConfig createWebShellConfig();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        webShellConfig = createWebShellConfig();
        if (webShellConfig == null || webShellConfig.getStartUrl().isEmpty()) {
            throw new IllegalStateException("AiEngineWebShellConfig with non-empty startUrl is required.");
        }

        FrameLayout rootView = new FrameLayout(this);
        rootView.setLayoutParams(new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
        ));
        applySystemBarInsets(rootView);

        webView = new WebView(this);
        webView.setLayoutParams(new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
        ));

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setLoadWithOverviewMode(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setCacheMode(WebSettings.LOAD_NO_CACHE);
        settings.setUseWideViewPort(true);
        webView.addJavascriptInterface(new AndroidBridge(), webShellConfig.getBridgeName());
        webView.clearCache(true);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                Log.i(TAG, "Page finished: " + url);
                playMutedVideos(view);
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                super.onReceivedError(view, request, error);
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.M) {
                    Log.e(TAG, "Page error: " + request.getUrl() + " " + error.getErrorCode() + " " + error.getDescription());
                }
            }
        });
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onConsoleMessage(ConsoleMessage consoleMessage) {
                Log.i(
                        TAG,
                        "Console " + consoleMessage.messageLevel()
                                + " " + consoleMessage.sourceId()
                                + ":" + consoleMessage.lineNumber()
                                + " " + consoleMessage.message()
                );
                return super.onConsoleMessage(consoleMessage);
            }

            @Override
            public void onPermissionRequest(PermissionRequest request) {
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        Log.i(TAG, "Permission request: " + joinResources(request.getResources()));
                        if (pendingAudioPermissionRequest != null && pendingAudioPermissionRequest != request) {
                            pendingAudioPermissionRequest.deny();
                            pendingAudioPermissionRequest = null;
                            pendingAudioPermissionResources = null;
                        }

                        String[] grantedResources = getAllowedWebViewResources(request);
                        if (grantedResources.length == 0) {
                            request.deny();
                            return;
                        }

                        if (!hasRecordAudioPermission()) {
                            Log.i(TAG, "Android RECORD_AUDIO not granted; requesting system permission.");
                            pendingAudioPermissionRequest = request;
                            pendingAudioPermissionResources = grantedResources;
                            requestRecordAudioPermission();
                            return;
                        }

                        Log.i(TAG, "Granting WebView resources: " + joinResources(grantedResources));
                        request.grant(grantedResources);
                    }
                });
            }

            @Override
            public void onPermissionRequestCanceled(PermissionRequest request) {
                if (pendingAudioPermissionRequest == request) {
                    pendingAudioPermissionRequest = null;
                    pendingAudioPermissionResources = null;
                }
            }

            @Override
            public boolean onShowFileChooser(
                    WebView view,
                    ValueCallback<Uri[]> filePathCallback,
                    FileChooserParams fileChooserParams
            ) {
                if (pendingWebFilePathCallback != null) {
                    pendingWebFilePathCallback.onReceiveValue(null);
                }
                pendingWebFilePathCallback = filePathCallback;

                try {
                    startActivityForResult(fileChooserParams.createIntent(), REQUEST_WEB_FILE_CHOOSER);
                    return true;
                } catch (Exception error) {
                    Log.e(TAG, "Unable to open WebView file chooser.", error);
                    pendingWebFilePathCallback = null;
                    filePathCallback.onReceiveValue(null);
                    return false;
                }
            }
        });
        rootView.addView(webView);
        setContentView(rootView);

        if (savedInstanceState == null) {
            webView.loadUrl(webShellConfig.getStartUrl());
        } else {
            webView.restoreState(savedInstanceState);
        }

        if (webShellConfig.isUpdateCheckEnabled()) {
            checkForUpdates();
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        webView.saveState(outState);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != REQUEST_RECORD_AUDIO) {
            return;
        }

        recordAudioPermissionRequestInFlight = false;
        boolean granted = grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED;
        if (pendingAudioPermissionRequest == null) {
            notifyMicrophonePermissionResult(granted);
            return;
        }

        if (granted) {
            Log.i(TAG, "Android RECORD_AUDIO granted; granting pending WebView request.");
            pendingAudioPermissionRequest.grant(pendingAudioPermissionResources);
        } else {
            Log.i(TAG, "Android RECORD_AUDIO denied; denying pending WebView request.");
            pendingAudioPermissionRequest.deny();
        }

        pendingAudioPermissionRequest = null;
        pendingAudioPermissionResources = null;
        notifyMicrophonePermissionResult(granted);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        if (requestCode == REQUEST_WEB_FILE_CHOOSER) {
            handleWebFileChooserResult(resultCode, data);
            return;
        }

        if (requestCode == REQUEST_BRIDGE_FILE_CHOOSER) {
            handleBridgeFileChooserResult(resultCode, data);
        }
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
            return;
        }

        super.onBackPressed();
    }

    @Override
    protected void onDestroy() {
        if (pendingAudioPermissionRequest != null) {
            pendingAudioPermissionRequest.deny();
            pendingAudioPermissionRequest = null;
            pendingAudioPermissionResources = null;
        }
        if (webView != null) {
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }

    private boolean hasRecordAudioPermission() {
        return android.os.Build.VERSION.SDK_INT < android.os.Build.VERSION_CODES.M
                || checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED;
    }

    private void requestRecordAudioPermission() {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.M) {
            if (recordAudioPermissionRequestInFlight) {
                return;
            }
            recordAudioPermissionRequestInFlight = true;
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQUEST_RECORD_AUDIO);
        }
    }

    private void notifyMicrophonePermissionResult(boolean granted) {
        if (webView == null) {
            return;
        }
        String script = "window.dispatchEvent(new CustomEvent('ai-engine-android-microphone-permission',"
                + "{detail:{granted:" + granted + "}}));";
        webView.evaluateJavascript(script, null);
    }

    private void dispatchNativeActionResult(String action, boolean success, String message) {
        evaluateJavascript(AiEngineBridgeEvent.nativeActionResult(action, success, message));
    }

    private void dispatchFileSelection(String requestId, List<AiEngineSelectedFile> files, boolean cancelled, String error) {
        evaluateJavascript(AiEngineBridgeEvent.fileSelection(requestId, files, cancelled, error));
    }

    private void evaluateJavascript(String script) {
        if (webView == null || script == null || script.isEmpty()) {
            return;
        }
        webView.evaluateJavascript(script, null);
    }

    private void applySystemBarInsets(FrameLayout rootView) {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.M) {
            getWindow().setStatusBarColor(Color.TRANSPARENT);
            getWindow().setNavigationBarColor(Color.TRANSPARENT);
        }

        rootView.setOnApplyWindowInsetsListener(new View.OnApplyWindowInsetsListener() {
            @Override
            public WindowInsets onApplyWindowInsets(View view, WindowInsets insets) {
                view.setPadding(
                        insets.getSystemWindowInsetLeft(),
                        insets.getSystemWindowInsetTop(),
                        insets.getSystemWindowInsetRight(),
                        insets.getSystemWindowInsetBottom()
                );
                return insets;
            }
        });
        rootView.requestApplyInsets();
    }

    private void playMutedVideos(WebView view) {
        view.evaluateJavascript(
                "(function(){"
                        + "if(window.__aiEnginePlayMutedVideos){clearInterval(window.__aiEnginePlayMutedVideos);}"
                        + "var attempts=0;"
                        + "function playVideos(){"
                        + "document.querySelectorAll('video').forEach(function(video){"
                        + "video.muted=true;"
                        + "video.loop=true;"
                        + "video.setAttribute('playsinline','');"
                        + "video.setAttribute('webkit-playsinline','');"
                        + "video.play().catch(function(){});"
                        + "});"
                        + "attempts+=1;"
                        + "if(attempts>=20){clearInterval(window.__aiEnginePlayMutedVideos);window.__aiEnginePlayMutedVideos=null;}"
                        + "}"
                        + "playVideos();"
                        + "window.__aiEnginePlayMutedVideos=setInterval(playVideos,500);"
                        + "})();",
                null
        );
    }

    private String[] getAllowedWebViewResources(PermissionRequest request) {
        List<String> allowed = new ArrayList<>();
        for (String resource : request.getResources()) {
            if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(resource)) {
                allowed.add(resource);
            }
        }
        return allowed.toArray(new String[0]);
    }

    private String joinResources(String[] resources) {
        StringBuilder builder = new StringBuilder();
        for (int index = 0; index < resources.length; index += 1) {
            if (index > 0) {
                builder.append(",");
            }
            builder.append(resources[index]);
        }
        return builder.toString();
    }

    private void checkForUpdates() {
        if (updateCheckStarted) {
            return;
        }
        updateCheckStarted = true;

        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    UpdateInfo updateInfo = fetchUpdateInfo();
                    if (updateInfo == null || updateInfo.build <= getCurrentVersionCode()) {
                        return;
                    }

                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            showUpdateDialog(updateInfo);
                        }
                    });
                } catch (Exception ignored) {
                    // Update checks should never block the WebView app itself.
                }
            }
        }).start();
    }

    private UpdateInfo fetchUpdateInfo() throws Exception {
        if (webShellConfig.getUpdateManifestUrl().isEmpty()) {
            return null;
        }

        URL url = new URL(webShellConfig.getUpdateManifestUrl() + "?t=" + System.currentTimeMillis());
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setConnectTimeout(8000);
        connection.setReadTimeout(8000);
        connection.setRequestMethod("GET");

        try {
            int statusCode = connection.getResponseCode();
            if (statusCode < 200 || statusCode >= 300) {
                return null;
            }

            JSONObject json = new JSONObject(readStream(connection.getInputStream()));
            int build = parsePositiveInt(json.optString("build", ""));
            if (build <= 0) {
                return null;
            }

            String versionName = firstNonEmpty(
                    json.optString("versionShort", ""),
                    json.optString("versionName", ""),
                    json.optString("version", "")
            );
            String updateUrl = firstNonEmpty(
                    json.optString("update_url", ""),
                    json.optString("updateUrl", ""),
                    json.optString("install_url", ""),
                    json.optString("installUrl", ""),
                    webShellConfig.getDefaultUpdateUrl()
            );
            String changelog = json.optString("changelog", "").trim();
            return new UpdateInfo(build, versionName, updateUrl, changelog);
        } finally {
            connection.disconnect();
        }
    }

    private String readStream(InputStream stream) throws Exception {
        StringBuilder builder = new StringBuilder();
        BufferedReader reader = new BufferedReader(new InputStreamReader(stream, "UTF-8"));
        try {
            String line;
            while ((line = reader.readLine()) != null) {
                builder.append(line);
            }
            return builder.toString();
        } finally {
            reader.close();
        }
    }

    private void showUpdateDialog(final UpdateInfo updateInfo) {
        if (isFinishing()
                || (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.JELLY_BEAN_MR1 && isDestroyed())) {
            return;
        }

        StringBuilder message = new StringBuilder();
        message.append("当前版本：")
                .append(getCurrentVersionName())
                .append(" (")
                .append(getCurrentVersionCode())
                .append(")");

        if (!updateInfo.versionName.isEmpty()) {
            message.append("\n最新版本：")
                    .append(updateInfo.versionName)
                    .append(" (")
                    .append(updateInfo.build)
                    .append(")");
        } else {
            message.append("\n最新版本：")
                    .append(updateInfo.build);
        }

        if (!updateInfo.changelog.isEmpty()) {
            message.append("\n\n更新内容：\n")
                    .append(updateInfo.changelog);
        }

        new AlertDialog.Builder(this)
                .setTitle("发现新版本")
                .setMessage(message.toString())
                .setPositiveButton("去升级", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface dialog, int which) {
                        openUpdateUrl(updateInfo.updateUrl);
                    }
                })
                .setNegativeButton("稍后", null)
                .show();
    }

    private void openUpdateUrl(String url) {
        try {
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
            startActivity(intent);
        } catch (Exception ignored) {
            webView.loadUrl(url);
        }
    }

    private boolean startNativeActivity(String actionName, Intent intent) {
        try {
            startActivity(intent);
            dispatchNativeActionResult(actionName, true, "");
            return true;
        } catch (Exception error) {
            Log.e(TAG, "Native action failed: " + actionName, error);
            dispatchNativeActionResult(actionName, false, error.getMessage());
            return false;
        }
    }

    private void handleWebFileChooserResult(int resultCode, Intent data) {
        if (pendingWebFilePathCallback == null) {
            return;
        }

        Uri[] results = WebChromeClient.FileChooserParams.parseResult(resultCode, data);
        pendingWebFilePathCallback.onReceiveValue(results);
        pendingWebFilePathCallback = null;
    }

    private void handleBridgeFileChooserResult(int resultCode, Intent data) {
        String requestId = pendingBridgeFileRequestId;
        pendingBridgeFileRequestId = null;

        if (requestId == null) {
            return;
        }

        if (resultCode != RESULT_OK || data == null) {
            dispatchFileSelection(requestId, new ArrayList<AiEngineSelectedFile>(), true, "");
            return;
        }

        try {
            dispatchFileSelection(requestId, collectSelectedFiles(data), false, "");
        } catch (Exception error) {
            Log.e(TAG, "Unable to read selected file metadata.", error);
            dispatchFileSelection(requestId, new ArrayList<AiEngineSelectedFile>(), false, error.getMessage());
        }
    }

    private List<AiEngineSelectedFile> collectSelectedFiles(Intent data) {
        List<AiEngineSelectedFile> files = new ArrayList<>();
        ClipData clipData = data.getClipData();
        if (clipData != null) {
            for (int index = 0; index < clipData.getItemCount(); index += 1) {
                Uri uri = clipData.getItemAt(index).getUri();
                if (uri != null) {
                    files.add(describeSelectedFile(uri));
                }
            }
            return files;
        }

        Uri uri = data.getData();
        if (uri != null) {
            files.add(describeSelectedFile(uri));
        }
        return files;
    }

    private AiEngineSelectedFile describeSelectedFile(Uri uri) {
        String name = "";
        long size = -1L;
        String mimeType = firstNonEmpty(getContentResolver().getType(uri), "");

        Cursor cursor = getContentResolver().query(uri, null, null, null, null);
        if (cursor != null) {
            try {
                if (cursor.moveToFirst()) {
                    int nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                    if (nameIndex >= 0) {
                        name = firstNonEmpty(cursor.getString(nameIndex), "");
                    }

                    int sizeIndex = cursor.getColumnIndex(OpenableColumns.SIZE);
                    if (sizeIndex >= 0 && !cursor.isNull(sizeIndex)) {
                        size = cursor.getLong(sizeIndex);
                    }
                }
            } finally {
                cursor.close();
            }
        }

        return new AiEngineSelectedFile(uri.toString(), name, mimeType, size);
    }

    private void openBridgeFileChooser(String requestId, String acceptTypes, boolean allowMultiple) {
        if (pendingBridgeFileRequestId != null) {
            dispatchNativeActionResult("chooseFile", false, "已有文件选择请求进行中。");
            return;
        }

        pendingBridgeFileRequestId = firstNonEmpty(requestId, String.valueOf(System.currentTimeMillis()));
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, allowMultiple);

        String[] mimeTypes = parseMimeTypes(acceptTypes);
        intent.setType(mimeTypes.length == 1 ? mimeTypes[0] : "*/*");
        if (mimeTypes.length > 1) {
            intent.putExtra(Intent.EXTRA_MIME_TYPES, mimeTypes);
        }

        try {
            startActivityForResult(Intent.createChooser(intent, "选择文件"), REQUEST_BRIDGE_FILE_CHOOSER);
            dispatchNativeActionResult("chooseFile", true, "");
        } catch (Exception error) {
            pendingBridgeFileRequestId = null;
            Log.e(TAG, "Unable to open bridge file chooser.", error);
            dispatchNativeActionResult("chooseFile", false, error.getMessage());
        }
    }

    private String[] parseMimeTypes(String acceptTypes) {
        String[] tokens = valueOrEmpty(acceptTypes).split(",");
        List<String> mimeTypes = new ArrayList<>();

        for (String token : tokens) {
            String value = token.trim();
            if (value.isEmpty() || value.startsWith(".")) {
                continue;
            }
            if (value.contains("/")) {
                mimeTypes.add(value);
            }
        }

        if (mimeTypes.isEmpty()) {
            mimeTypes.add("*/*");
        }
        return mimeTypes.toArray(new String[0]);
    }

    private int getCurrentVersionCode() {
        try {
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.P) {
                return (int) getPackageManager().getPackageInfo(getPackageName(), 0).getLongVersionCode();
            }
            return getPackageManager().getPackageInfo(getPackageName(), 0).versionCode;
        } catch (Exception ignored) {
            return 0;
        }
    }

    private String getCurrentVersionName() {
        try {
            String versionName = getPackageManager().getPackageInfo(getPackageName(), 0).versionName;
            return versionName == null ? "" : versionName;
        } catch (Exception ignored) {
            return "";
        }
    }

    private int parsePositiveInt(String value) {
        try {
            return Integer.parseInt(value.trim());
        } catch (Exception ignored) {
            return 0;
        }
    }

    private String firstNonEmpty(String... values) {
        for (String value : values) {
            if (value != null && !value.trim().isEmpty()) {
                return value.trim();
            }
        }
        return "";
    }

    private String valueOrEmpty(String value) {
        return value == null ? "" : value.trim();
    }

    private Intent buildSystemSettingsIntent(String target) {
        String normalized = valueOrEmpty(target).toLowerCase(Locale.US);
        if ("app".equals(normalized) || "application".equals(normalized)) {
            return new Intent(
                    Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                    Uri.parse("package:" + getPackageName())
            );
        }

        if ("wifi".equals(normalized)) {
            return new Intent(Settings.ACTION_WIFI_SETTINGS);
        }

        if ("bluetooth".equals(normalized)) {
            return new Intent(Settings.ACTION_BLUETOOTH_SETTINGS);
        }

        if ("accessibility".equals(normalized)) {
            return new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS);
        }

        if ("notification".equals(normalized)) {
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                return new Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS)
                        .putExtra(Settings.EXTRA_APP_PACKAGE, getPackageName());
            }
            return new Intent(
                    Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                    Uri.parse("package:" + getPackageName())
            );
        }

        return new Intent(Settings.ACTION_SETTINGS);
    }

    private static final class UpdateInfo {
        final int build;
        final String versionName;
        final String updateUrl;
        final String changelog;

        UpdateInfo(int build, String versionName, String updateUrl, String changelog) {
            this.build = build;
            this.versionName = versionName;
            this.updateUrl = updateUrl;
            this.changelog = changelog;
        }
    }

    private final class AndroidBridge {
        @JavascriptInterface
        public boolean hasMicrophonePermission() {
            return hasRecordAudioPermission();
        }

        @JavascriptInterface
        public void requestMicrophonePermission() {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    if (hasRecordAudioPermission()) {
                        notifyMicrophonePermissionResult(true);
                        return;
                    }
                    requestRecordAudioPermission();
                }
            });
        }

        @JavascriptInterface
        public void openAppSettings() {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    startNativeActivity("openAppSettings", buildSystemSettingsIntent("app"));
                }
            });
        }

        @JavascriptInterface
        public void openSystemSettings(final String target) {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    startNativeActivity("openSystemSettings", buildSystemSettingsIntent(target));
                }
            });
        }

        @JavascriptInterface
        public void openUrl(final String url) {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    String normalizedUrl = valueOrEmpty(url);
                    if (normalizedUrl.isEmpty()) {
                        dispatchNativeActionResult("openUrl", false, "URL 不能为空。");
                        return;
                    }
                    startNativeActivity("openUrl", new Intent(Intent.ACTION_VIEW, Uri.parse(normalizedUrl)));
                }
            });
        }

        @JavascriptInterface
        public void openIntent(final String action, final String dataUri, final String mimeType) {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    Intent intent = new Intent(firstNonEmpty(action, Intent.ACTION_VIEW));
                    String normalizedDataUri = valueOrEmpty(dataUri);
                    String normalizedMimeType = valueOrEmpty(mimeType);

                    if (!normalizedDataUri.isEmpty() && !normalizedMimeType.isEmpty()) {
                        intent.setDataAndType(Uri.parse(normalizedDataUri), normalizedMimeType);
                    } else if (!normalizedDataUri.isEmpty()) {
                        intent.setData(Uri.parse(normalizedDataUri));
                    } else if (!normalizedMimeType.isEmpty()) {
                        intent.setType(normalizedMimeType);
                    }

                    startNativeActivity("openIntent", intent);
                }
            });
        }

        @JavascriptInterface
        public void shareText(final String title, final String text, final String url) {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    String shareText = firstNonEmpty(text, "");
                    String shareUrl = valueOrEmpty(url);
                    if (!shareUrl.isEmpty()) {
                        shareText = shareText.isEmpty() ? shareUrl : shareText + "\n" + shareUrl;
                    }

                    if (shareText.isEmpty()) {
                        dispatchNativeActionResult("shareText", false, "分享内容不能为空。");
                        return;
                    }

                    Intent sendIntent = new Intent(Intent.ACTION_SEND);
                    sendIntent.setType("text/plain");
                    sendIntent.putExtra(Intent.EXTRA_TEXT, shareText);
                    String shareTitle = firstNonEmpty(title, "分享");
                    startNativeActivity("shareText", Intent.createChooser(sendIntent, shareTitle));
                }
            });
        }

        @JavascriptInterface
        public void chooseFile(final String requestId, final String acceptTypes, final boolean allowMultiple) {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    openBridgeFileChooser(requestId, acceptTypes, allowMultiple);
                }
            });
        }
    }
}
