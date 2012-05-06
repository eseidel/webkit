# Copyright (C) 2012 Google Inc. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# 1.  Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
# 2.  Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


# These constants help make the feature list easier to read/edit.
MacLion = "AppleMacLion"  # 10.7, Apple disables a couple features on Lion, which are not disabled on later versions of the OS.
Mac = "AppleMac"
Win = "AppleWin"
IOS = "AppleIOS"
WinCairo = "WinCairo"
BlackBerry = "BlackBerry"
Efl = "Efl"
Gtk = "Gtk"
Qt = "Qt"


class Feature(object):
    def _to_set(self, value):
        value = value or []
        if type(value) is not list:
            value = [value]
        return set(value)

    def __init__(self, name, default=True, enable=None, disable=None):
        self.name = name
        self.enable = self._to_set(enable)
        self.disable = self._to_set(disable)
        self.default = default

    def define_name(self):
        return "ENABLE_" + self.name

    def is_enabled(self, port_name):
        if port_name in self.disable:
            return False
        if port_name in self.enable:
            return True
        return self.default


# This list is meant to be a global list of default enable/disable values
# for features, across all ports of WebKit.
#
# The "default" key, specifies how to treat the feature on ports which are not
# explicitly listed.
#
# The Feature() syntax supports both white-list (enable=) and blacklist (disable=).
# A single Feature line can include both, but normally default=True features
# use blacklists, and default=False features use whitelists.
#
# The enable= and disable= processing is smart enough to handle either single values
# e.g. enable=Mac, or lists enable=[Mac, Win].
#
# Normally if you're adding a feature, you should start with default=False and
# an explicit white-list of ports which want to support that feature:
# Feature("MY_FEATURE", default=False)
#
# Once a Feature is widly supported, "default" should change to True, and a
# blacklist used for brevity.

features = [
    Feature("3D_RENDERING", disable=WinCairo),
    Feature("ACCELERATED_2D_CANVAS", default=False),
    Feature("ANIMATION_API", default=False, enable=BlackBerry),
    Feature("BATTERY_STATUS", default=False, enable=[BlackBerry, Efl]),
    Feature("BLOB", disable=[Win, WinCairo]),
    Feature("CHANNEL_MESSAGING"),
    Feature("CSS_EXCLUSIONS", default=False),
    Feature("CSS_FILTERS", default=False, enable=[Mac, Win, Qt, IOS]),
    Feature("CSS_GRID_LAYOUT", disable=[Win, WinCairo, Qt]),
    Feature("CSS_REGIONS", default=False),
    Feature("CSS_SHADERS", default=False),
    Feature("DASHBOARD_SUPPORT", default=False, enable=Mac),
    Feature("DATA_TRANSFER_ITEMS", default=False),
    Feature("DATAGRID", default=False),
    Feature("DATALIST", default=False, enable=[WinCairo, Qt]),
    Feature("DETAILS"),
    Feature("DEVICE_ORIENTATION", default=False, enable=BlackBerry),
    Feature("DIRECTORY_UPLOAD", default=False),
    Feature("DOWNLOAD_ATTRIBUTE", default=False, enable=BlackBerry),
    Feature("FAST_MOBILE_SCROLLING", default=False, enable=Qt),
    Feature("FILE_SYSTEM", default=False, enable=BlackBerry),
    Feature("FILTERS", disable=IOS),
    Feature("FTPDIR"),
    Feature("FULLSCREEN_API", disable=[WinCairo, Qt]),
    Feature("GAMEPAD", default=False),
    Feature("GEOLOCATION", disable=[Efl, Qt]),
    Feature("GESTURE_EVENTS", default=False, enable=Qt),
    Feature("HIGH_DPI_CANVAS", default=False, enable=[Mac, Win, IOS]),
    Feature("ICONDATABASE", disable=IOS),
    Feature("INDEXED_DATABASE", default=False),
    Feature("INPUT_SPEECH", default=False),
    Feature("INPUT_TYPE_COLOR", default=False, enable=[BlackBerry, Efl]),
    Feature("INPUT_TYPE_DATE", default=False, enable=IOS),
    Feature("INPUT_TYPE_DATETIME", default=False, enable=IOS),
    Feature("INPUT_TYPE_DATETIMELOCAL", default=False, enable=IOS),
    Feature("INPUT_TYPE_MONTH", default=False, enable=IOS),
    Feature("INPUT_TYPE_TIME", default=False, enable=IOS),
    Feature("INPUT_TYPE_WEEK", default=False, enable=IOS),
    Feature("INSPECTOR"),
    Feature("JAVASCRIPT_DEBUGGER"),
    Feature("LEGACY_CSS_VENDOR_PREFIXES", default=False, enable=[Mac, Win, IOS]),
    Feature("LEGACY_NOTIFICATIONS", default=False, enable=[Mac, BlackBerry, Qt], disable=MacLion),
    Feature("LEGACY_WEBKIT_BLOB_BUILDER", default=False, enable=Qt),
    Feature("LINK_PREFETCH", default=False),
    Feature("LINK_PRERENDER", default=False),
    Feature("MATHML", default=False, enable=[Mac, Win, IOS]),
    Feature("MEDIA_SOURCE", default=False, enable=Win),
    Feature("MEDIA_STATISTICS", default=False, enable=Win),
    Feature("MEDIA_STREAM", default=False),
    Feature("METER_TAG"),
    Feature("MHTML", default=False),
    Feature("MICRODATA", default=False),
    Feature("MUTATION_OBSERVERS", disable=Qt),
    Feature("NETSCAPE_PLUGIN_API", disable=[Qt, IOS]),
    Feature("NETWORK_INFO", default=False, enable=Efl),
    Feature("NOTIFICATIONS", default=False, enable=[Mac, Qt], disable=MacLion),
    Feature("ORIENTATION_EVENTS", default=False, enable=BlackBerry),
    Feature("PAGE_VISIBILITY_API", default=False, enable=Qt),
    Feature("PROGRESS_TAG", disable=[Win, WinCairo]),
    Feature("QUOTA", default=False),
    Feature("REGISTER_PROTOCOL_HANDLER", default=False),
    Feature("REQUEST_ANIMATION_FRAME", disable=WinCairo),
    Feature("SCRIPTED_SPEECH", default=False),
    Feature("SHADOW_DOM", default=False, enable=Gtk),
    Feature("SHARED_WORKERS"),
    Feature("SQL_DATABASE"),
    Feature("STYLE_SCOPED", default=False),
    Feature("SVG"),
    Feature("SVG_DOM_OBJC_BINDINGS", default=False, enable=Mac),
    Feature("SVG_FONTS", disable=Qt),
    Feature("TEXT_NOTIFICATIONS_ONLY", default=False, enable=[Mac, IOS]), # IOS likely doesn't want this.
    Feature("TOUCH_ADJUSTMENT", default=False, enable=Qt),
    Feature("TOUCH_EVENTS", default=False, enable=Qt),
    Feature("TOUCH_ICON_LOADING", default=False),
    Feature("VIBRATION", default=False, enable=[BlackBerry, Efl]),
    Feature("VIDEO", disable=[WinCairo, Qt]),
    Feature("VIDEO_TRACK", default=False, enable=Mac),
    Feature("WEB_AUDIO", disable=[Win, WinCairo, Qt]),
    Feature("WEB_SOCKETS"),
    Feature("WEB_TIMING", default=False, enable=[BlackBerry, Gtk, Efl, Qt]),
    Feature("WEBGL", disable=[Win, WinCairo, Qt]),
    Feature("WORKERS"),
    Feature("XSLT", disable=Qt),
]
