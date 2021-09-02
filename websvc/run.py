import os
from app import app

http_host = "127.0.0.1" # listen on local host
http_port = 5000 # flask listening port

if __name__ == "__main__":
    port = int(os.environ.get("PORT", http_port))
    app.run(host=http_host, port=port, debug=True)