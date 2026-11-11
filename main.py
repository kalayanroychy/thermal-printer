from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.utils import platform
from kivy.clock import Clock
import threading
import json
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler

def show_toast(message):
    if platform == 'android':
        try:
            from jnius import autoclass
            from android.runnable import run_on_ui_thread
            Toast = autoclass('android.widget.Toast')
            String = autoclass('java.lang.String')
            Activity = autoclass('org.kivy.android.PythonActivity').mActivity
            
            @run_on_ui_thread
            def _toast():
                Toast.makeText(Activity, String(message[:150]), Toast.LENGTH_LONG).show()
            _toast()
        except:
            pass
    print("TOAST:", message)

def do_actual_print(mac_address, text_to_print, qr_code='', logo_hex='', base64_raw=''):
    if platform != 'android':
        print("Bluetooth print only works on Android!")
        return

    try:
        show_toast("Step 1: Starting print process...")
        from jnius import autoclass
        BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
        UUID = autoclass('java.util.UUID')
        
        show_toast("Step 2: Getting BT Adapter...")
        adapter = BluetoothAdapter.getDefaultAdapter()
        if adapter is None or not adapter.isEnabled():
            show_toast("Error: Bluetooth is OFF or not available!")
            return
            
        if mac_address:
            mac_address = mac_address.strip()
            
        if not mac_address:
            show_toast("Step 3: Auto-selecting paired printer...")
            paired_devices = adapter.getBondedDevices().toArray()
            if not paired_devices or len(paired_devices) == 0:
                show_toast("Error: No paired Bluetooth devices found!")
                return
            device = paired_devices[0]
            mac_address = device.getAddress()
            show_toast(f"Selected device: {device.getName()} ({mac_address})")
        else:
            show_toast(f"Step 3: Getting device {mac_address}...")
            device = adapter.getRemoteDevice(mac_address)
        
        show_toast("Step 4: Creating Socket...")
        MY_UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")
        socket = device.createRfcommSocketToServiceRecord(MY_UUID)
        
        show_toast("Step 5: Connecting Socket...")
        socket.connect()
        
        show_toast("Step 6: Getting Output Stream...")
        out_stream = socket.getOutputStream()
        
        show_toast("Step 7: Sending Data...")
        
        if base64_raw:
            try:
                import base64
                raw_bytes = base64.b64decode(base64_raw)
                # Init printer
                out_stream.write(bytes([0x1B, 0x40]))
                # Center alignment
                out_stream.write(bytes([0x1B, 0x61, 0x01]))
                # Write the image bytes
                out_stream.write(raw_bytes)
                # Feed lines
                out_stream.write(b'\x0A\x0A\x0A\x0A')
            except Exception as e:
                print("Image Print Error:", e)
        else:
            # Print Logo (if provided in hex)
            if logo_hex:
                try:
                    out_stream.write(bytes.fromhex(logo_hex))
                except Exception as le:
                    print("Logo Print Error:", le)
            else:
                # Init printer if no logo is printed
                magic_init = [0x1B, 0x40]
                out_stream.write(bytes(magic_init))
                
            out_stream.write(text_to_print.encode('utf-8'))
            
            if qr_code:
                try:
                    # Ensure we are on a new line before printing QR code
                    out_stream.write(b'\x0A')
                    # Center alignment for QR
                    out_stream.write(b'\x1B\x61\x01')
                    # Select QR model 2
                    out_stream.write(b'\x1D\x28\x6B\x04\x00\x31\x41\x32\x00')
                    # Set module size to 4 (6 is often too big for 58mm printers)
                    out_stream.write(b'\x1D\x28\x6B\x03\x00\x31\x43\x04')
                    # Set error correction to M
                    out_stream.write(b'\x1D\x28\x6B\x03\x00\x31\x45\x31')
                    
                    # Store data
                    qr_data = qr_code.encode('utf-8')
                    qr_len = len(qr_data) + 3
                    pL = qr_len % 256
                    pH = qr_len // 256
                    out_stream.write(b'\x1D\x28\x6B' + bytes([pL, pH]) + b'\x31\x50\x30' + qr_data)
                    
                    # Print QR code
                    out_stream.write(b'\x1D\x28\x6B\x03\x00\x31\x51\x30')
                    # Reset alignment
                    out_stream.write(b'\x1B\x61\x00')
                except Exception as qr_e:
                    print("QR Print Error:", qr_e)
        
            # Line feed
            out_stream.write(b'\x0A\x0A\x0A') 
            
        out_stream.flush()
        
        show_toast("Step 8: Printed Successfully!")
        socket.close()
        
    except Exception as e:
        err_msg = f"Print Error: {str(e)}"
        show_toast(err_msg)
        print(traceback.format_exc())
        try:
            socket.close()
        except:
            pass

def print_to_bluetooth(mac_address, text_to_print, qr_code='', logo_hex='', base64_raw=''):
    # Kivy's Clock might be paused when Android WebView takes over the ContentView.
    # Therefore, we use a standard background thread to run pyjnius printing logic.
    threading.Thread(target=do_actual_print, args=(mac_address, text_to_print, qr_code, logo_hex, base64_raw), daemon=True).start()

def get_android_gps_location():
    if platform != 'android':
        return None
    try:
        from jnius import autoclass
        Context = autoclass('android.content.Context')
        Activity = autoclass('org.kivy.android.PythonActivity').mActivity
        location_manager = Activity.getSystemService(Context.LOCATION_SERVICE)
        if location_manager is None:
            return None

        providers = ['gps', 'network', 'passive']
        best_loc = None
        for p in providers:
            try:
                if location_manager.isProviderEnabled(p):
                    loc = location_manager.getLastKnownLocation(p)
                    if loc is not None:
                        if best_loc is None or loc.getAccuracy() < best_loc.getAccuracy():
                            best_loc = loc
            except:
                pass

        if best_loc is not None:
            return {
                'status': 'ok',
                'lat': float(best_loc.getLatitude()),
                'lng': float(best_loc.getLongitude())
            }
    except Exception as e:
        print("GPS Error:", e)
    return None

class PrintAPIHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        if self.path.startswith('/gps'):
            loc = get_android_gps_location()
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            if loc:
                self.wfile.write(json.dumps(loc).encode('utf-8'))
            else:
                self.wfile.write(b'{"status": "unavailable"}')
        else:
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "running", "app": "DhopaMamaApp"}')

    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            text_to_print = data.get('text', '')
            base64_raw = data.get('base64Raw', '')
            mac_address = data.get('mac', '')
            qr_code = data.get('qrCode', '')
            logo_hex = data.get('logoHex', '')
            
            if not text_to_print and not base64_raw:
                self.send_response(400)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                return

            # Trigger the print function
            print_to_bluetooth(mac_address, text_to_print, qr_code, logo_hex, base64_raw)
            
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "success"}')
        except Exception as e:
            err = f"API Error: {str(e)}"
            show_toast(err)
            print(traceback.format_exc())
            
            # Always return 200 to prevent the website from falling back to intent://
            # even if printing failed (e.g. bluetooth disabled or no printer)
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "error", "message": "Check phone Bluetooth"}')

def run_local_server():
    try:
        server = HTTPServer(('127.0.0.1', 8080), PrintAPIHandler)
        server.serve_forever()
    except Exception as e:
        show_toast(f"Server crash: {str(e)}")

ANDROID_WEBVIEW = None

def open_android_webview(url):
    if platform != 'android':
        return
        
    try:
        from jnius import autoclass
        from android.runnable import run_on_ui_thread

        WebView = autoclass('android.webkit.WebView')
        WebViewClient = autoclass('android.webkit.WebViewClient')
        WebChromeClient = autoclass('android.webkit.WebChromeClient')
        Activity = autoclass('org.kivy.android.PythonActivity').mActivity
        
        @run_on_ui_thread
        def create_webview():
            global ANDROID_WEBVIEW
            try:
                webview = WebView(Activity)
                settings = webview.getSettings()
                settings.setJavaScriptEnabled(True)
                settings.setDomStorageEnabled(True)
                settings.setDatabaseEnabled(True)
                settings.setGeolocationEnabled(True)
                settings.setAllowFileAccess(True)
                settings.setMixedContentMode(0) 
                
                # Append custom string to User-Agent to identify the Kivy App
                current_ua = settings.getUserAgentString()
                settings.setUserAgentString(current_ua + " DhopaMamaApp")

                webview.setWebViewClient(WebViewClient())
                webview.setWebChromeClient(WebChromeClient())
                webview.loadUrl(url)
                
                Activity.setContentView(webview)
                ANDROID_WEBVIEW = webview
            except Exception as e:
                show_toast(f"Init Error: {str(e)}")
                
        create_webview()
    except Exception as e:
        show_toast(f"WebView Error: {str(e)}")


class PrinterApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical', padding=50)
        layout.add_widget(Label(text="Loading ধোপা মামা... Please wait."))
        
        server_thread = threading.Thread(target=run_local_server, daemon=True)
        server_thread.start()
        
        return layout

    def on_start(self):
        if platform == 'android':
            try:
                from kivy.core.window import Window
                Window.bind(on_keyboard=self.on_back_button)
            except:
                pass

            try:
                from android.permissions import request_permissions, Permission
                perms = [
                    Permission.BLUETOOTH_CONNECT,
                    Permission.BLUETOOTH_SCAN,
                    Permission.BLUETOOTH,
                    Permission.BLUETOOTH_ADMIN,
                    Permission.INTERNET,
                    Permission.ACCESS_FINE_LOCATION,
                    Permission.ACCESS_COARSE_LOCATION,
                    Permission.CAMERA
                ]
                try:
                    perms.append(Permission.POST_NOTIFICATIONS)
                except:
                    perms.append("android.permission.POST_NOTIFICATIONS")
                request_permissions(perms)
            except:
                pass
            
        target_url = "http://103.25.81.14:8401" 
        open_android_webview(target_url)

    def on_back_button(self, window, key, *args):
        if key == 27 and platform == 'android' and ANDROID_WEBVIEW is not None:
            try:
                from android.runnable import run_on_ui_thread
                @run_on_ui_thread
                def _go_back():
                    try:
                        if ANDROID_WEBVIEW.canGoBack():
                            ANDROID_WEBVIEW.goBack()
                    except:
                        pass
                _go_back()
                return True
            except:
                pass
        return False

if __name__ == '__main__':
    PrinterApp().run()
