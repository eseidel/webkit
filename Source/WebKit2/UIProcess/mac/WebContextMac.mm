/*
 * Copyright (C) 2010 Apple Inc. All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY APPLE INC. AND ITS CONTRIBUTORS ``AS IS''
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
 * THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
 * PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL APPLE INC. OR ITS CONTRIBUTORS
 * BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
 * THE POSSIBILITY OF SUCH DAMAGE.
 */

#import "config.h"
#import "WebContext.h"

#import "PluginProcessManager.h"
#import "SharedWorkerProcessManager.h"
#import "WKBrowsingContextControllerInternal.h"
#import "WKBrowsingContextControllerInternal.h"
#import "WebKitSystemInterface.h"
#import "WebProcessCreationParameters.h"
#import "WebProcessMessages.h"
#import <QuartzCore/CARemoteLayerServer.h>
#import <WebCore/Color.h>
#import <WebCore/FileSystem.h>
#import <WebCore/NotImplemented.h>
#import <WebCore/PlatformPasteboard.h>
#import <sys/param.h>

#if ENABLE(NETWORK_PROCESS)
#import "NetworkProcessCreationParameters.h"
#import "NetworkProcessProxy.h"
#endif

using namespace WebCore;

NSString *WebDatabaseDirectoryDefaultsKey = @"WebDatabaseDirectory";
NSString *WebKitLocalCacheDefaultsKey = @"WebKitLocalCache";
NSString *WebStorageDirectoryDefaultsKey = @"WebKitLocalStorageDatabasePathPreferenceKey";
NSString *WebKitKerningAndLigaturesEnabledByDefaultDefaultsKey = @"WebKitKerningAndLigaturesEnabledByDefault";

static NSString *WebKitApplicationDidChangeAccessibilityEnhancedUserInterfaceNotification = @"NSApplicationDidChangeAccessibilityEnhancedUserInterfaceNotification";

// FIXME: <rdar://problem/9138817> - After this "backwards compatibility" radar is removed, this code should be removed to only return an empty String.
NSString *WebIconDatabaseDirectoryDefaultsKey = @"WebIconDatabaseDirectoryDefaultsKey";

static NSString * const WebKit2HTTPProxyDefaultsKey = @"WebKit2HTTPProxy";
static NSString * const WebKit2HTTPSProxyDefaultsKey = @"WebKit2HTTPSProxy";

namespace WebKit {

NSString *SchemeForCustomProtocolRegisteredNotificationName = @"WebKitSchemeForCustomProtocolRegisteredNotification";
NSString *SchemeForCustomProtocolUnregisteredNotificationName = @"WebKitSchemeForCustomProtocolUnregisteredNotification";

bool WebContext::s_applicationIsOccluded = false;

static void registerUserDefaultsIfNeeded()
{
    static bool didRegister;
    if (didRegister)
        return;

    didRegister = true;
    NSMutableDictionary *registrationDictionary = [NSMutableDictionary dictionary];
    
#if __MAC_OS_X_VERSION_MIN_REQUIRED >= 1090
    [registrationDictionary setObject:[NSNumber numberWithBool:YES] forKey:WebKitKerningAndLigaturesEnabledByDefaultDefaultsKey];
#endif

    [[NSUserDefaults standardUserDefaults] registerDefaults:registrationDictionary];
}

void WebContext::platformInitialize()
{
    registerUserDefaultsIfNeeded();
    registerNotificationObservers();
}

String WebContext::applicationCacheDirectory()
{
    NSString *appName = [[NSBundle mainBundle] bundleIdentifier];
    if (!appName)
        appName = [[NSProcessInfo processInfo] processName];
    
    ASSERT(appName);
    
    NSUserDefaults *defaults = [NSUserDefaults standardUserDefaults];
    NSString *cacheDir = [defaults objectForKey:WebKitLocalCacheDefaultsKey];

    if (!cacheDir || ![cacheDir isKindOfClass:[NSString class]]) {
        char cacheDirectory[MAXPATHLEN];
        size_t cacheDirectoryLen = confstr(_CS_DARWIN_USER_CACHE_DIR, cacheDirectory, MAXPATHLEN);
    
        if (cacheDirectoryLen)
            cacheDir = [[NSFileManager defaultManager] stringWithFileSystemRepresentation:cacheDirectory length:cacheDirectoryLen - 1];
    }

    return [cacheDir stringByAppendingPathComponent:appName];
}

void WebContext::platformInitializeWebProcess(WebProcessCreationParameters& parameters)
{
    parameters.presenterApplicationPid = getpid();

    NSURLCache *urlCache = [NSURLCache sharedURLCache];
    parameters.nsURLCacheMemoryCapacity = [urlCache memoryCapacity];
    parameters.nsURLCacheDiskCapacity = [urlCache diskCapacity];

#if __MAC_OS_X_VERSION_MIN_REQUIRED >= 1090
    parameters.shouldForceScreenFontSubstitution = [[NSUserDefaults standardUserDefaults] boolForKey:@"NSFontDefaultScreenFontSubstitutionEnabled"];
#endif
    parameters.shouldEnableKerningAndLigaturesByDefault = [[NSUserDefaults standardUserDefaults] boolForKey:WebKitKerningAndLigaturesEnabledByDefaultDefaultsKey];

#if USE(ACCELERATED_COMPOSITING) && HAVE(HOSTED_CORE_ANIMATION)
    mach_port_t renderServerPort = [[CARemoteLayerServer sharedServer] serverPort];
    if (renderServerPort != MACH_PORT_NULL)
        parameters.acceleratedCompositingPort = CoreIPC::MachPort(renderServerPort, MACH_MSG_TYPE_COPY_SEND);
#endif

    // FIXME: This should really be configurable; we shouldn't just blindly allow read access to the UI process bundle.
    parameters.uiProcessBundleResourcePath = [[NSBundle mainBundle] resourcePath];
    SandboxExtension::createHandle(parameters.uiProcessBundleResourcePath, SandboxExtension::ReadOnly, parameters.uiProcessBundleResourcePathExtensionHandle);

    parameters.uiProcessBundleIdentifier = String([[NSBundle mainBundle] bundleIdentifier]);

#if ENABLE(NETWORK_PROCESS)
    if (!m_usesNetworkProcess) {
#endif
        for (NSString *scheme in [WKBrowsingContextController customSchemes])
            parameters.urlSchemesRegisteredForCustomProtocols.append(scheme);
#if ENABLE(NETWORK_PROCESS)
    }
#endif
}

#if ENABLE(NETWORK_PROCESS)
void WebContext::platformInitializeNetworkProcess(NetworkProcessCreationParameters& parameters)
{
    NSURLCache *urlCache = [NSURLCache sharedURLCache];
    parameters.nsURLCacheMemoryCapacity = [urlCache memoryCapacity];
    parameters.nsURLCacheDiskCapacity = [urlCache diskCapacity];

    parameters.parentProcessName = [[NSProcessInfo processInfo] processName];
    parameters.uiProcessBundleIdentifier = [[NSBundle mainBundle] bundleIdentifier];

    for (NSString *scheme in [WKBrowsingContextController customSchemes])
        parameters.urlSchemesRegisteredForCustomProtocols.append(scheme);

    parameters.httpProxy = [[NSUserDefaults standardUserDefaults] stringForKey:WebKit2HTTPProxyDefaultsKey];
    parameters.httpsProxy = [[NSUserDefaults standardUserDefaults] stringForKey:WebKit2HTTPSProxyDefaultsKey];
}
#endif

void WebContext::platformInvalidateContext()
{
    unregisterNotificationObservers();
}

String WebContext::platformDefaultDiskCacheDirectory() const
{
    RetainPtr<NSString> cachePath(AdoptNS, (NSString *)WKCopyFoundationCacheDirectory());
    if (!cachePath)
        cachePath = @"~/Library/Caches/com.apple.WebKit2.WebProcess";

    return [cachePath.get() stringByStandardizingPath];
}

String WebContext::platformDefaultCookieStorageDirectory() const
{
    notImplemented();
    return [@"" stringByStandardizingPath];
}

String WebContext::platformDefaultDatabaseDirectory() const
{
    NSString *databasesDirectory = [[NSUserDefaults standardUserDefaults] objectForKey:WebDatabaseDirectoryDefaultsKey];
    if (!databasesDirectory || ![databasesDirectory isKindOfClass:[NSString class]])
        databasesDirectory = @"~/Library/WebKit/Databases";
    return [databasesDirectory stringByStandardizingPath];
}

String WebContext::platformDefaultIconDatabasePath() const
{
    // FIXME: <rdar://problem/9138817> - After this "backwards compatibility" radar is removed, this code should be removed to only return an empty String.
    NSString *databasesDirectory = [[NSUserDefaults standardUserDefaults] objectForKey:WebIconDatabaseDirectoryDefaultsKey];
    if (!databasesDirectory || ![databasesDirectory isKindOfClass:[NSString class]])
        databasesDirectory = @"~/Library/Icons/WebpageIcons.db";
    return [databasesDirectory stringByStandardizingPath];
}

String WebContext::platformDefaultLocalStorageDirectory() const
{
    NSString *localStorageDirectory = [[NSUserDefaults standardUserDefaults] objectForKey:WebStorageDirectoryDefaultsKey];
    if (!localStorageDirectory || ![localStorageDirectory isKindOfClass:[NSString class]])
        localStorageDirectory = @"~/Library/WebKit/LocalStorage";
    return [localStorageDirectory stringByStandardizingPath];
}

bool WebContext::omitPDFSupport()
{
    // Since this is a "secret default" we don't bother registering it.
    return [[NSUserDefaults standardUserDefaults] boolForKey:@"WebKitOmitPDFSupport"];
}

void WebContext::getPasteboardTypes(const String& pasteboardName, Vector<String>& pasteboardTypes)
{
    PlatformPasteboard(pasteboardName).getTypes(pasteboardTypes);
}

void WebContext::getPasteboardPathnamesForType(const String& pasteboardName, const String& pasteboardType, Vector<String>& pathnames)
{
    PlatformPasteboard(pasteboardName).getPathnamesForType(pathnames, pasteboardType);
}

void WebContext::getPasteboardStringForType(const String& pasteboardName, const String& pasteboardType, String& string)
{
    string = PlatformPasteboard(pasteboardName).stringForType(pasteboardType);
}

void WebContext::getPasteboardBufferForType(const String& pasteboardName, const String& pasteboardType, SharedMemory::Handle& handle, uint64_t& size)
{
    RefPtr<SharedBuffer> buffer = PlatformPasteboard(pasteboardName).bufferForType(pasteboardType);
    if (!buffer)
        return;
    size = buffer->size();
    RefPtr<SharedMemory> sharedMemoryBuffer = SharedMemory::create(size);
    memcpy(sharedMemoryBuffer->data(), buffer->data(), size);
    sharedMemoryBuffer->createHandle(handle, SharedMemory::ReadOnly);
}

void WebContext::pasteboardCopy(const String& fromPasteboard, const String& toPasteboard)
{
    PlatformPasteboard(toPasteboard).copy(fromPasteboard);
}

void WebContext::getPasteboardChangeCount(const String& pasteboardName, uint64_t& changeCount)
{
    changeCount = PlatformPasteboard(pasteboardName).changeCount();
}

void WebContext::getPasteboardUniqueName(String& pasteboardName)
{
    pasteboardName = PlatformPasteboard::uniqueName();
}

void WebContext::getPasteboardColor(const String& pasteboardName, WebCore::Color& color)
{
    color = PlatformPasteboard(pasteboardName).color();    
}

void WebContext::getPasteboardURL(const String& pasteboardName, WTF::String& urlString)
{
    urlString = PlatformPasteboard(pasteboardName).url().string();
}

void WebContext::addPasteboardTypes(const String& pasteboardName, const Vector<String>& pasteboardTypes)
{
    PlatformPasteboard(pasteboardName).addTypes(pasteboardTypes);
}

void WebContext::setPasteboardTypes(const String& pasteboardName, const Vector<String>& pasteboardTypes)
{
    PlatformPasteboard(pasteboardName).setTypes(pasteboardTypes);
}

void WebContext::setPasteboardPathnamesForType(const String& pasteboardName, const String& pasteboardType, const Vector<String>& pathnames)
{
    PlatformPasteboard(pasteboardName).setPathnamesForType(pathnames, pasteboardType);
}

void WebContext::setPasteboardStringForType(const String& pasteboardName, const String& pasteboardType, const String& string)
{
    PlatformPasteboard(pasteboardName).setStringForType(string, pasteboardType);    
}

void WebContext::setPasteboardBufferForType(const String& pasteboardName, const String& pasteboardType, const SharedMemory::Handle& handle, uint64_t size)
{
    if (handle.isNull()) {
        PlatformPasteboard(pasteboardName).setBufferForType(0, pasteboardType);
        return;
    }
    RefPtr<SharedMemory> sharedMemoryBuffer = SharedMemory::create(handle, SharedMemory::ReadOnly);
    RefPtr<SharedBuffer> buffer = SharedBuffer::create(static_cast<unsigned char *>(sharedMemoryBuffer->data()), size);
    PlatformPasteboard(pasteboardName).setBufferForType(buffer, pasteboardType);
}

void WebContext::applicationBecameVisible(uint32_t, void*, uint32_t, void*, uint32_t)
{
    if (s_applicationIsOccluded) {
        s_applicationIsOccluded = false;

        const Vector<WebContext*>& contexts = WebContext::allContexts();
        for (size_t i = 0, count = contexts.size(); i < count; ++i) {
#if ENABLE(NETWORK_PROCESS)
            if (contexts[i]->usesNetworkProcess() && contexts[i]->networkProcess())
                contexts[i]->networkProcess()->setApplicationIsOccluded(false);
#endif

            contexts[i]->sendToAllProcesses(Messages::WebProcess::SetApplicationIsOccluded(false));
        }

#if ENABLE(PLUGIN_PROCESS)
        PluginProcessManager::shared().setApplicationIsOccluded(false);
#endif
#if ENABLE(SHARED_WORKER_PROCESS)
        SharedWorkerProcessManager::shared().setApplicationIsOccluded(false);
#endif
    }
}

void WebContext::applicationBecameOccluded(uint32_t, void*, uint32_t, void*, uint32_t)
{
    if (!s_applicationIsOccluded) {
        s_applicationIsOccluded = true;
        const Vector<WebContext*>& contexts = WebContext::allContexts();
        for (size_t i = 0, count = contexts.size(); i < count; ++i) {
#if ENABLE(NETWORK_PROCESS)
            if (contexts[i]->usesNetworkProcess() && contexts[i]->networkProcess())
                contexts[i]->networkProcess()->setApplicationIsOccluded(true);
#endif

            contexts[i]->sendToAllProcesses(Messages::WebProcess::SetApplicationIsOccluded(true));
        }

#if ENABLE(PLUGIN_PROCESS)
        PluginProcessManager::shared().setApplicationIsOccluded(true);
#endif
#if ENABLE(SHARED_WORKER_PROCESS)
        SharedWorkerProcessManager::shared().setApplicationIsOccluded(true);
#endif
    }
}

void WebContext::initializeProcessSuppressionSupport()
{
    static bool didInitialize = false;
    if (didInitialize)
        return;

    didInitialize = true;
    // A temporary default until process suppression is enabled by default, at which point a context setting can be added with the
    // interpretation that any context disabling process suppression disables it for plugin/network and shared worker processes.
    bool processSuppressionSupportEnabled = [[NSUserDefaults standardUserDefaults] boolForKey:@"WebKitProcessSuppressionSupportEnabled"];
    if (processSuppressionSupportEnabled)
        registerOcclusionNotificationHandlers();
}

void WebContext::registerOcclusionNotificationHandlers()
{
#if __MAC_OS_X_VERSION_MIN_REQUIRED >= 1090
    if (!WKRegisterOcclusionNotificationHandler(WKOcclusionNotificationTypeApplicationBecameVisible, applicationBecameVisible)) {
        WTFLogAlways("Registeration of \"App Became Visible\" notification handler failed.\n");
        return;
    }

    if (!WKRegisterOcclusionNotificationHandler(WKOcclusionNotificationTypeApplicationBecameOccluded, applicationBecameOccluded))
        WTFLogAlways("Registeration of \"App Became Occluded\" notification handler failed.\n");
#endif
}
    
void WebContext::registerNotificationObservers()
{
    m_customSchemeRegisteredObserver = [[NSNotificationCenter defaultCenter] addObserverForName:WebKit::SchemeForCustomProtocolRegisteredNotificationName object:nil queue:[NSOperationQueue currentQueue] usingBlock:^(NSNotification *notification) {
        NSString *scheme = [notification object];
        ASSERT([scheme isKindOfClass:[NSString class]]);
        registerSchemeForCustomProtocol(scheme);
    }];
    
    m_customSchemeUnregisteredObserver = [[NSNotificationCenter defaultCenter] addObserverForName:WebKit::SchemeForCustomProtocolUnregisteredNotificationName object:nil queue:[NSOperationQueue currentQueue] usingBlock:^(NSNotification *notification) {
        NSString *scheme = [notification object];
        ASSERT([scheme isKindOfClass:[NSString class]]);
        unregisterSchemeForCustomProtocol(scheme);
    }];
    
    // Listen for enhanced accessibility changes and propagate them to the WebProcess.
    m_enhancedAccessibilityObserver = [[NSNotificationCenter defaultCenter] addObserverForName:WebKitApplicationDidChangeAccessibilityEnhancedUserInterfaceNotification object:nil queue:[NSOperationQueue currentQueue] usingBlock:^(NSNotification *note) {
        setEnhancedAccessibility([[[note userInfo] objectForKey:@"AXEnhancedUserInterface"] boolValue]);
    }];
}

void WebContext::unregisterNotificationObservers()
{
    [[NSNotificationCenter defaultCenter] removeObserver:(id)m_customSchemeRegisteredObserver.get()];
    [[NSNotificationCenter defaultCenter] removeObserver:(id)m_customSchemeUnregisteredObserver.get()];
    [[NSNotificationCenter defaultCenter] removeObserver:(id)m_enhancedAccessibilityObserver.get()];
}

} // namespace WebKit
