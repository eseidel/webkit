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

from webkitpy.tool.multicommandtool import AbstractDeclarativeCommand

import imp
import string

class FeatureFileGenerator(object):
    _warning_lines = """This is a generated file. Do not edit.
This file is generated from Source/Features.py using
webkit-patch generate-feature-files""".split("\n")

    def __init__(self, features_module):
        self.features_module = features_module
        self.features = sorted(features_module.features, key=lambda feature: feature.name)

    def _all_defines(self):
        return sorted([feature.define_name() for feature in self.features])


class XCConfigGenerator(FeatureFileGenerator):
    _header = "\n".join(["// %s" % line for line in FeatureFileGenerator._warning_lines]) + "\n"

    def _content_for_feature(self, feature):
        define_name = feature.define_name()
        on_mac = feature.is_enabled(self.features_module.Mac)
        on_ios = feature.is_enabled(self.features_module.IOS)

        if on_mac == on_ios and self.features_module.MacLion not in feature.excludes:
            return "%s = %s;\n" % (define_name, define_name if on_mac else "")

        content = "%s = $(%s_$(REAL_PLATFORM_NAME));\n" % (define_name, define_name)
        if on_mac:
            # NOTE: This code is not general-purpose for version specification
            # this is just enough to make ENABLE_NOTIFICATION be disabled on Lion.
            if self.features_module.MacLion in feature.excludes:
                content += "%s_macosx = $(%s_macosx_$(TARGET_MAC_OS_X_VERSION_MAJOR));\n" % (define_name, define_name)
                content += "%s_macosx_1070 = ;\n" % (define_name)
                content += "%s_macosx_1080 = %s;\n" % (define_name, define_name)
                content += "%s_macosx_1090 = %s;\n" % (define_name, define_name)
            else:
                content += "%s_macosx = %s;\n" % (define_name, define_name)
        if on_ios:
            content += "%s_iphoneos = %s;\n" % (define_name, define_name)
            content += "%s_iphonesimulator = %s;\n" % (define_name, define_name)
        return content

    def generate(self):
        # The same file is used by Mac and IOS, so taking a port_name would be meaningless.
        contents = self._header
        for feature in self.features:
            contents += self._content_for_feature(feature)
        contents += "\nFEATURE_DEFINES = %s;\n" % " ".join(["$(%s)" % name for name in self._all_defines()])
        return contents


class VSPropsGenerator(FeatureFileGenerator):

    def _generate_header(self, file_name):
        header = '<?xml version="1.0" encoding="utf-8"?>\n'
        header += "\n".join(["<!-- %s -->" % line for line in FeatureFileGenerator._warning_lines]) + "\n"
        header += """<VisualStudioPropertySheet
\tProjectType="Visual C++"
\tVersion="8.00"
\tName="%s"
\t>
""" % file_name
        return header

    _footer = "</VisualStudioPropertySheet>\n"

    def _content_for_feature(self, feature, port_name):
        define_name = feature.define_name()
        enabled_name = define_name if feature.is_enabled(port_name) else ""
        return """  <UserMacro
\t\tName="%s"
\t\tValue="%s"
\t\tPerformEnvironmentSet="true"
\t/>\n""" % (define_name, enabled_name)

    def generate_for_port(self, port_name, file_name):
        contents = self._generate_header(file_name)
        all_defines_string = ";".join(["$(%s)" % name for name in self._all_defines()])
        contents += """  <Tool
\t\tName="VCCLCompilerTool"
\t\tPreprocessorDefinitions="%s"
\t/>\n""" % all_defines_string

        for feature in self.features:
            contents += self._content_for_feature(feature, port_name)
        return contents + self._footer


class BuildWebKitOptionsGenerator(FeatureFileGenerator):
    # Presumably we could make this header/footer be less verbose. :(
    _header = ("\n".join(["# %s" % line for line in FeatureFileGenerator._warning_lines]) + "\n" +
        '''use strict;
use warnings;

use FindBin;
use lib $FindBin::Bin;
use webkitdirs;

BEGIN {
   use Exporter   ();
   our ($VERSION, @ISA, @EXPORT, @EXPORT_OK, %EXPORT_TAGS);
   $VERSION     = 1.00;
   @ISA         = qw(Exporter);
   @EXPORT      = qw(&getFeatureOptionList);
   %EXPORT_TAGS = ( );
   @EXPORT_OK   = ();
}''')

    _footer = """
sub getFeatureOptionList()
{
    return @features;
}

1;
"""

    def _value_name_for_feature(self, feature):
        value_name = "".join(word.capitalize() for word in feature.name.split("_"))
        if (value_name[:2] == "3d"):
            value_name = "threeD" + value_name[2:]
        value_name = value_name[:1].lower() + value_name[1:] + "Support"
        return self._fix_capitalization(value_name)

    def _option_name_for_feature(self, feature):
        return feature.name.lower().replace("_", "-")

    def _option_text_for_feature(self, feature):
        option_text = "Toggle %s support" % " ".join(word.capitalize() for word in feature.name.split("_"))
        return self._fix_capitalization(option_text)

    # FIXME: This function is only needed until replace FeatureList.pm with an autogenerated list the first time.
    def _fix_capitalization(self, feature_name):
        replacements = [
            ["2d", "2D"],
            ["3d", "3D"],
            ["Api", "API"],
            ["Css", "CSS"],
            ["Dom", "DOM"],
            ["Dpi", "DPI"],
            ["Javascript", "JavaScript"],
            ["Mathml", "MathML"],
            ["Mhtml", "MHTML"],
            ["Objc", "ObjC"],
            ["Sql", "SQL"],
            ["Svg", "SVG"],
            ["Xslt", "XSLT"],
        ]
        for replacement in replacements:
            feature_name = feature_name.replace(*replacement)
        return feature_name

    def _perl_function_for_port_name(self, port_name):
        return {
            self.features_module.Mac: "isAppleMacWebkit()",
            self.features_module.Win: "isAppleWinWebkit()",
            self.features_module.BlackBerry: "isBlackBerry()",
            self.features_module.Efl: "isEfl()",
            self.features_module.Gtk: "isGtk()",
            self.features_module.Qt: "isQt()",
        }[port_name]

    def _default_string_for_feature(self, feature):
        # build-webkit doesn't know how to build IOS or WinCairo, so we don't care about those inclusions/exclusions.
        ignored_port_names = set([self.features_module.IOS, self.features_module.WinCairo])
        excluded_port_names = sorted(feature.excludes - ignored_port_names)
        included_port_names = sorted(feature.includes - ignored_port_names)
        if excluded_port_names or included_port_names:
            # FIXME: This is the hard part. :)
            if not excluded_port_names:
                port_names_string = " || ".join([self._perl_function_for_port_name(port_name) for port_name in included_port_names])
                if len(included_port_names) > 1:
                    return "(%s)" % port_names_string
                return port_names_string
            elif not included_port_names:
                port_names_string = " && ".join(["!" + self._perl_function_for_port_name(port_name) for port_name in excluded_port_names])
                if len(included_port_names) > 1:
                    return "(%s)" % port_names_string
                return port_names_string
            return "ERROR"
        return "1" if feature.default_enabled else "0"

    def _options_dictionary_string_for_feature(self, feature):
        option_name = self._option_name_for_feature(feature)
        option_text = self._option_text_for_feature(feature)
        define_name = feature.define_name()
        default_string = self._default_string_for_feature(feature)
        value_name = self._value_name_for_feature(feature)
        return """    { option => "%s", desc => "%s",
      define => "%s", default => %s, value => \$%s },""" % (option_name, option_text, define_name, default_string, value_name)

    def generate(self):
        contents = self._header
        contents += "\n\nmy (\n"
        contents += "\n".join(["    $%s," % self._value_name_for_feature(feature) for feature in self.features])
        contents += "\n);\n\nmy @features = (\n"
        contents += "\n\n".join([self._options_dictionary_string_for_feature(feature) for feature in self.features])
        contents += "\n);\n";
        return contents + self._footer


class QMakePRIGenerator(FeatureFileGenerator):
    _header = "\n".join(["# %s" % line for line in FeatureFileGenerator._warning_lines]) + "\n"

    def generate_for_port(self, port_name):
        contents = self._header
        contents += "FEATURE_DEFAULTS = \\\n"
        for feature in self.features:
            define_string = feature.define_name() + "=" + ("1" if feature.is_enabled(port_name) else "0")
            contents += "    %s \\\n" % define_string
        return contents + "\n"


class GenerateFeatureFiles(AbstractDeclarativeCommand):
    name = "generate-feature-files"
    help_text = "Command for generating per-port feature files from Source/Features"

    def execute(self, options, args, tool):
        fs = tool.filesystem
        webkit_root = tool.scm().checkout_root
        features_list_path = fs.join(webkit_root, "Source", "Features.py")
        features_module = imp.load_source('features', features_list_path)

        xcconfig_projects = [
            'WebCore',
            'JavaScriptCore',
            'WebKit2',
            'WebKit/mac',
        ]
        xcconfig_features = XCConfigGenerator(features_module).generate()
        for project_name in xcconfig_projects:
            feature_file_path = fs.join(webkit_root, "Source", project_name, "Configurations", "FeatureDefines.xcconfig")
            fs.write_text_file(feature_file_path, xcconfig_features)

        vsprops_generator = VSPropsGenerator(features_module)
        vsprops_dir = fs.join(webkit_root, "WebKitLibraries", "win", "tools", "vsprops")

        vsprops_features = vsprops_generator.generate_for_port(features_module.Win, "FeatureDefines")
        fs.write_text_file(fs.join(vsprops_dir, "FeatureDefines.vsprops"), vsprops_features)

        vsprops_features = vsprops_generator.generate_for_port(features_module.WinCairo, "FeatureDefinesCairo")
        fs.write_text_file(fs.join(vsprops_dir, "FeatureDefinesCairo.vsprops"), vsprops_features)

        build_webkit_features = BuildWebKitOptionsGenerator(features_module).generate()
        fs.write_text_file(fs.join(webkit_root, "Tools", "Scripts", "webkitperl", "FeatureList.pm"), build_webkit_features)

        qmake_pri_features = QMakePRIGenerator(features_module).generate_for_port(features_module.Qt)
        fs.write_text_file(fs.join(webkit_root, "Tools", "qmake", "mkspecs", "features", "features.pri"), qmake_pri_features)

