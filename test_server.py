from flask import Flask
test_app = Flask(__name__)

@test_app.route('/')
def index():
    return "Test server works!"

if __name__ == '__main__':
    test_app.run(host='0.0.0.0', port=5000, debug=False)
