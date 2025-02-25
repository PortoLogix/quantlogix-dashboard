from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def home():
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Flask Test</title>
        </head>
        <body>
            <h1>Flask Test Page</h1>
            <p>If you can see this, Flask is working!</p>
            <button onclick="alert('Button clicked!')">Click me!</button>
        </body>
        </html>
    """)

if __name__ == '__main__':
    app.run(host='localhost', port=8510, debug=True)
