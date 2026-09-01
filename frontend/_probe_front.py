import urllib.request
import urllib.error

for url in ["http://localhost:3000/", "http://localhost:3000/command-center", "http://localhost:3000/ai-employees"]:
    try:
        r = urllib.request.urlopen(url, timeout=60)
        body = r.read().decode("utf-8", "replace")
        print(f"{url} -> HTTP {r.status}, {len(body)} bytes")
        # Look for error markers
        for marker in ["__next_error__", "Application error", "Internal Server Error", "Unhandled Runtime Error"]:
            if marker in body:
                i = body.find(marker)
                print("   MARKER:", marker)
                print("   context:", body[max(0, i-200):i+300].replace("\n", " ")[:400])
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        print(f"{url} -> HTTP {e.code}, {len(body)} bytes")
        for marker in ["__next_error__", "Application error", "Internal Server Error", "Unhandled Runtime Error", "error"]:
            i = body.find(marker)
            if i >= 0:
                print("   context:", body[max(0, i-200):i+400].replace("\n", " ")[:500])
                break
    except Exception as e:
        print(f"{url} -> FAILED: {e}")
    print()
