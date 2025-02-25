from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return """
    <html>
        <body>
            <h1 style="color: blue;">Minimal Test</h1>
            <p>If you see this, Flask is working!</p>
            <script>
                console.log('Page loaded');
                document.body.style.backgroundColor = '#f0f0f0';
            </script>
        </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='localhost', port=8514)
