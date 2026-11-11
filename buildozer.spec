[app]
title = DhopaMama
package.name = dhopamama
package.domain = org.test
source.dir = .
icon.filename = %(source.dir)s/logo.png
source.include_exts = py,png,jpg,kv,atlas,xml
source.exclude_dirs = bin,obj,.vs,.git,Migrations,Controllers,Models,Views,Areas,Data,Services,Properties,wwwroot
version = 0.3
requirements = python3,kivy,android,pyjnius
orientation = portrait
fullscreen = 0
android.permissions = INTERNET, BLUETOOTH, BLUETOOTH_ADMIN, BLUETOOTH_CONNECT, BLUETOOTH_SCAN, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION, CAMERA, POST_NOTIFICATIONS
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.accept_sdk_license = True
android.extra_manifest_application_arguments = %(source.dir)s/extra_args.xml
ios.codesign.allowed = false
p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 0
