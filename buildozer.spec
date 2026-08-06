[app]
title = DhopaMama
package.name = dhopamama
package.domain = org.test
source.dir = .
icon.filename = %(source.dir)s/logo.png
source.include_exts = py,png,jpg,kv,atlas
version = 0.1
requirements = python3,kivy,android,pyjnius
orientation = portrait
fullscreen = 0
android.permissions = INTERNET, BLUETOOTH, BLUETOOTH_ADMIN, BLUETOOTH_CONNECT, BLUETOOTH_SCAN
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.accept_sdk_license = True
android.extra_manifest_application_arguments = %(source.dir)s/extra_args.xml
ios.codesign.allowed = false
p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 0
