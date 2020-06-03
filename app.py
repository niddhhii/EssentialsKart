from flask import Flask, request, make_response, jsonify
from firebase import firebase
import firebase_admin
from firebase_admin import credentials

from datetime import date

app = Flask(__name__)


@app.route('/')
def index():
    return 'Hello World!'


def getAction():
    req = request.get_json(force=True)
    action = req.get('queryResult').get('action')
    return action


def pushToDB():
    firebase_obj = firebase.FirebaseApplication('https://essentials-kart.firebaseio.com/', None)
    req = request.get_json(force=True)
    params = req.get('queryResult').get('parameters')
    sess = req.get('session')[-36:] + "-" + str(date.today())
    print(sess)
    curr_sess = firebase_obj.get('/orders', sess, connection=None)
    if curr_sess is None:
        print(1)
        item_list = params['items']
        num_list = params['number']
        order_dict = {}
        for i in range(len(item_list)):
            temp = [item_list[i], num_list[i]]
            order_dict.update({i: temp})
        sess_dict = {sess: order_dict}
        print(sess_dict)
    else:
        print(2)
        item_list = params['items']
        num_list = params['number']
        sess = []
        for i in range(len(item_list)):
            temp = [item_list[i], num_list[i]]
            sess.append(temp)
        print(sess)
        # session['sess'] = sess

    result = firebase_obj.post('/actions', sess_dict, connection=None)
    print(result)


@app.route('/webhook', methods=['POST'])
def webhook():
    action = getAction()
    # print(action)
    if action == 'order_items':  # save items to session
        pushToDB()
        reply = {
            "fulfillmentText": "Order Items",
        }
        return make_response(jsonify(reply))
    elif action == 'input.welcome':  # send the items pdf
        reply = {
            "fulfillmentText": "Send PDF",
        }
        return make_response(jsonify(reply))
    elif action == 'OrderItems.OrderItems-cancel':  # delete the session and end it
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


if __name__ == '__main__':
    cred = credentials.Certificate("firebase-adminsdk.json")
    firebase_admin.initialize_app(cred)
    app.run()
