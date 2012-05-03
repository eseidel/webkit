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

# Used by Scripts/webkitpy/tool/commands/generatefeaturefiles.py when generating
# the build-webkit options list where we must translate the feature defaults to perl.
all_port_names = [Mac, Win, IOS, WinCairo, BlackBerry, Efl]


class Feature(object):
    default_enabled = True

    def _to_set(self, value):
        value = value or []
        if type(value) is not list:
            value = [value]
        return set(value)

    def __init__(self, name, exclude=None, include=None):
        self.name = name
        self.excludes = self._to_set(exclude)
        self.includes = self._to_set(include)

    def define_name(self):
        return "ENABLE_" + self.name

    def is_enabled(self, port_name):
        if port_name in self.excludes:
            return False
        if port_name in self.includes:
            return True
        return self.default_enabled


# Disabled features use a white-list approach, instead of a blacklist.
class DisabledFeature(Feature):
    default_enabled = False


features = [
    DisabledFeature("3D_CANVAS"),
    Feature("3D_RENDERING", exclude=WinCairo),
    DisabledFeature("ACCELERATED_2D_CANVAS"),
    DisabledFeature("ANIMATION_API", include=BlackBerry),
    Feature("BLOB", exclude=[Win, WinCairo]),
    Feature("CHANNEL_MESSAGING"),
    DisabledFeature("CSS_EXCLUSIONS"),
    Feature("CSS_FILTERS", exclude=WinCairo),
    DisabledFeature("CSS_SHADERS"),
    DisabledFeature("CSS_REGIONS"),
    Feature("CSS_GRID_LAYOUT", exclude=[Win, WinCairo]),
    DisabledFeature("DASHBOARD_SUPPORT", include=Mac),
    DisabledFeature("DATALIST", include=WinCairo),
    DisabledFeature("DATAGRID"),
    DisabledFeature("DATA_TRANSFER_ITEMS"),
    Feature("DETAILS"),
    DisabledFeature("DEVICE_ORIENTATION"),
    DisabledFeature("DIRECTORY_UPLOAD"),
    DisabledFeature("FILE_SYSTEM"),
    Feature("FILTERS", exclude=IOS),
    Feature("FULLSCREEN_API", exclude=WinCairo),
    DisabledFeature("GAMEPAD"),
    Feature("GEOLOCATION"),
    Feature("HIGH_DPI_CANVAS", exclude=WinCairo),
    Feature("ICONDATABASE", exclude=IOS),
    DisabledFeature("INDEXED_DATABASE"),
    DisabledFeature("INPUT_SPEECH"),
    DisabledFeature("INPUT_TYPE_COLOR", include=[BlackBerry, Efl]),
    DisabledFeature("INPUT_TYPE_DATE", include=IOS),
    DisabledFeature("INPUT_TYPE_DATETIME", include=IOS),
    DisabledFeature("INPUT_TYPE_DATETIMELOCAL", include=IOS),
    DisabledFeature("INPUT_TYPE_MONTH", include=IOS),
    DisabledFeature("INPUT_TYPE_TIME", include=IOS),
    DisabledFeature("INPUT_TYPE_WEEK", include=IOS),
    Feature("JAVASCRIPT_DEBUGGER"),
    Feature("LEGACY_CSS_VENDOR_PREFIXES", exclude=WinCairo),
    DisabledFeature("LEGACY_NOTIFICATIONS", include=Mac, exclude=MacLion),
    DisabledFeature("LINK_PREFETCH"),
    DisabledFeature("LINK_PRERENDER"),
    Feature("MATHML"),
    DisabledFeature("MEDIA_SOURCE", include=Win),
    DisabledFeature("MEDIA_STATISTICS", include=Win),
    Feature("METER_TAG"),
    DisabledFeature("MHTML"),
    DisabledFeature("MICRODATA"),
    Feature("MUTATION_OBSERVERS"),
    DisabledFeature("NOTIFICATIONS", include=Mac, exclude=MacLion),
    DisabledFeature("PAGE_VISIBILITY_API"),
    Feature("PROGRESS_TAG", exclude=[Win, WinCairo]),
    DisabledFeature("QUOTA"),
    DisabledFeature("REGISTER_PROTOCOL_HANDLER"),
    Feature("REQUEST_ANIMATION_FRAME", exclude=WinCairo),
    DisabledFeature("SCRIPTED_SPEECH"),
    DisabledFeature("SHADOW_DOM"),
    Feature("SHARED_WORKERS"),
    Feature("SQL_DATABASE"),
    DisabledFeature("STYLE_SCOPED"),
    Feature("SVG"),
    DisabledFeature("SVG_DOM_OBJC_BINDINGS", include=Mac),
    Feature("SVG_FONTS"),
    Feature("TEXT_NOTIFICATIONS_ONLY", exclude=[Win, WinCairo]),
    DisabledFeature("TOUCH_ICON_LOADING"),
    Feature("VIDEO", exclude=WinCairo),
    DisabledFeature("VIDEO_TRACK", include=Mac),
    Feature("WEBGL", exclude=[Win, WinCairo]),
    Feature("WEB_AUDIO", exclude=[Win, WinCairo]),
    Feature("WEB_SOCKETS"),
    DisabledFeature("WEB_TIMING"),
    Feature("WORKERS"),
    Feature("XSLT"),
]
