# import flask dependencies
from flask import Flask, request, make_response, jsonify

# initialize the flask app
app = Flask(__name__)


# default route
@app.route('/')
def index():
    return 'Hello World!'


def getAction():
    req = request.get_json(force=True)
    action = req.get('queryResult').get('action')
    return action


# create a route for webhook
@app.route('/webhook')
def webhook():
    action = getAction()
    if action == 'order_items':  # save items to session
        reply = {
            "fulfillmentText": "Order Items",
        }
        return make_response(jsonify(reply))
    elif action == 'welcome':  # send the items pdf
        reply = {
            "fulfillmentText": "Send PDF",
        }
        return make_response(jsonify(reply))
    elif action == 'cancel_order':  # delete the session and end it
        reply = {
            "fulfillmentText": "Order Cancelled",
        }
        return make_response(jsonify(reply))
    elif action == 'confirm_details':  # ask for confirmation about order
        reply = {
            "fulfillmentText": "Details Confirmed",
        }
        return make_response(jsonify(reply))
    elif action == 'confirm_order':  # send final receipt over email and wapp
        reply = {
            "fulfillmentText": "Order confirmed",
        }
        return make_response(jsonify(reply))


# run the app
if __name__ == '__main__':
    app.run()
