import csv
from datetime import date

import pyrebase
from firebase import firebase
from flask import Flask, request, make_response, jsonify
from jinja2 import Environment, FileSystemLoader
from twilio.rest import Client

import config

app = Flask(__name__)

config = {
    "apiKey": config.apikey,
    "authDomain": config.authDomain,
    "databaseURL": config.databaseURL,
    "storageBucket": config.storageBucket,
    "serviceAccount": config.firebasesdk,
    "twilioSID": config.twilioSID,
    "twilioAUTH": config.twilioAUTH
}

firebaseObj = pyrebase.initialize_app(config)
fb_app = firebase.FirebaseApplication(config['databaseURL'], None)


@app.route('/')
def index():
    return 'Hello World!'


def getAction():
    req = request.get_json(force=True)
    action = req.get('queryResult').get('action')
    return action


def pushToDB():
    db = firebaseObj.database()
    req = request.get_json(force=True)
    params = req.get('queryResult').get('parameters')
    sess = req.get('session')[-13:] + "-" + str(date.today())
    curr_orders = fb_app.get('/orders', sess)
    if curr_orders is not None:
        item_list = params['items']
        num_list = params['number']
        order_dict = curr_orders
        poslist = []
        neglist = []
        for i in range(len(item_list)):
            price = get_price(item_list[i])
            if item_list[i] not in order_dict:
                if price != -1:
                    temp = {item_list[i]: [int(num_list[i]), price]}
                    order_dict.update(temp)
                    poslist.append(item_list[i])
                else:
                    neglist.append(item_list[i])
            else:
                prev = order_dict[item_list[i]][0]
                order_dict[item_list[i]][0] = prev + int(num_list[i])
                poslist.append(item_list[i])
        db.child('orders').child(sess).update(order_dict)
    else:
        item_list = params['items']
        num_list = params['number']
        order_dict = {}
        poslist = []
        neglist = []
        for i in range(len(item_list)):
            price = get_price(item_list[i])
            if price != -1:
                temp = {item_list[i]: [int(num_list[i]), price]}
                order_dict.update(temp)
                poslist.append(item_list[i])
            else:
                neglist.append(item_list[i])
        db.child('orders').child(sess).set(order_dict)
    text = ""
    if len(neglist) != 0:
        i = 0
        text = "Sorry, we don't sell "
        for item in neglist:
            if i == (len(neglist) - 2):
                text += item + " and "
            elif i == (len(neglist) - 1):
                text += item + ". "
            else:
                text += item + ", "
            i += 1
        text += "Please refer to the list we sent you earlier. "
        if len(poslist) != 0:
            text += "However, we have added "
            i = 0
            for item in poslist:
                if i == (len(poslist) - 2):
                    text += item + " and "
                elif i == (len(poslist) - 1):
                    text += item
                else:
                    text += item + ", "
                i += 1
            text += " to your cart."
    return text


def get_price(item):
    with open('items.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                line_count += 1
                continue
            else:
                if row[0] == item:
                    return int(row[1])
        return -1


def sendPDF(url):
    req = request.get_json(force=True)
    username = config['twilioSID']
    password = config['twilioAUTH']
    client = Client(username=username, password=password)
    from_whatsapp_number = 'whatsapp:+14155238886'
    to_whatsapp_number = req.get('session')[-13:]
    client.messages.create(body='EssentialsKart Products',
                           media_url=url,
                           from_=from_whatsapp_number,
                           to=to_whatsapp_number)
    ch_contact = fb_app.get('/users', to_whatsapp_number)
    if ch_contact is not None:
        name = ch_contact['name']
        client.messages.create(
            body='Hey ' + name + '! Glad to see you again. It\'s Natasha again from EssentialsKart. Here to help you '
                                 'out in your order. '
                                 'Please check the list below to find the essential items that you can order '
                                 'during lockdown. So, what would you like to order today?',
            from_=from_whatsapp_number,
            to=to_whatsapp_number)
    else:
        client.messages.create(
            body='Hey! I am Natasha from EssentialsKart. Here to help you out in your order. '
                 'Please check the list below to find the essential items that you can order '
                 'during lockdown. So, what would you like to order today?',
            from_=from_whatsapp_number,
            to=to_whatsapp_number)


def genPDF():
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template("invoice.html")
    template_vars = {"title": "Sales Funnel Report - National",
                     "national_pivot_table": ''}
    html_out = template.render(template_vars)
    # HTML(string=html_out).write_pdf("report.pdf")


def del_sess():
    req = request.get_json(force=True)
    sess = req.get('session')[-36:] + "-" + str(date.today())
    fb_app.delete('/orders', sess)


def check_phone():
    req = request.get_json(force=True)
    phone = req.get('session')[-13:]
    ch_contact = fb_app.get('/users', phone)
    if ch_contact is not None:
        name = ch_contact['name']
        return name + ", please enter your passcode to proceed."
    else:
        return "We have to setup an account for you to proceed further. Please enter your name."


def conf_details():
    req = request.get_json(force=True)
    details = req.get('queryResult').get('outputContexts')[2].get('parameters')
    contact = req.get('session')[-13:]
    db = firebaseObj.database()
    details_dict = {'name': details['name.original'].title(), 'email': details['email'], 'zipcode': details['zipcode']}
    db.child('users').child(contact).set(details_dict)
    return "Your account has been set up. Please enter a 4 digits passcode for future logins."


def get_order():
    req = request.get_json(force=True)
    sess = req.get('session')[-13:] + "-" + str(date.today())
    curr_orders = fb_app.get('/orders', sess)
    text = ""
    i = 1
    sums = 0
    for item in curr_orders:
        sums += curr_orders[item][0] * curr_orders[item][1]
        text += "{}. {}     {}  x    Rs. {}  =>  Rs. {}<br>".format(i, item.title(), curr_orders[item][0],
                                                                    curr_orders[item][1],
                                                                    (curr_orders[item][0] * curr_orders[item][1]))
        i += 1
    text += "Grand Total: {}<br>".format(sums)
    return text


def check_pwd():
    req = request.get_json(force=True)
    phone = req.get('session')[-13:]
    password = fb_app.get('/users', phone)['passcode']
    passcode = req.get('queryResult').get('parameters')['passcode']
    if password != passcode:
        return "Wrong passcode. Please try again."
    else:
        return "Authentication successful. Would you like to pay cash on delivery or by card?"


def add_pwd():
    req = request.get_json(force=True)
    phone = req.get('session')[-13:]
    passcode = req.get('queryResult').get('parameters')['new_passcode']
    ph = fb_app.get('/users', phone)
    if len(str(int(passcode))) == 4 and str(int(passcode)).isnumeric():
        ph.update({'passcode': passcode})
        db = firebaseObj.database()
        db.child('users').child(phone).update(ph)
        return "Congrats, " + ph['name'] + "! You are all set. Would you like to pay cash on delivery or by card?"
    else:
        return "Please enter a valid 4 digit numerical passcode."


def add_mode():
    req = request.get_json(force=True)
    phone = req.get('session')[-13:]
    mode = req.get('queryResult').get('parameters')['mop']
    ph = fb_app.get('/users', phone)
    ph.update({'mode': mode})
    db = firebaseObj.database()
    db.child('users').child(phone).update(ph)
    order = get_order()
    return "Please check your order details.<br>" + order + " Reply 'Yes' to confirm and 'No' to modify."


def conf_order():
    return ""


def edit_order():
    return ""


def edit_details():
    return ""


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    action = getAction()
    if action == 'order_items':  # save items to session
        text = pushToDB()
        reply = {
            "fulfillmentText": text,
        }
        return make_response(jsonify(reply))
    elif action == 'input.welcome':  # send the items pdf
        url = "https://github.com/ItsTheKayBee/chatbot-webhook-API/raw/master/price_list.pdf"
        # sendPDF(url)      # uncomment later
        reply = {
            "fulfillmentText": "",
        }
        return make_response(jsonify(reply))
    elif action == 'OrderItems.OrderItems-cancel':  # delete the session and end it
        del_sess()
        reply = {
            "fulfillmentText": "",
        }
        return make_response(jsonify(reply))
    elif action == 'confirm_details':  # ask for confirmation about order
        text = conf_details()
        reply = {
            "fulfillmentText": text,
        }
        return make_response(jsonify(reply))
    elif action == 'confirm_order':  # send final receipt over email and wapp
        text = conf_order()
        reply = {
            "fulfillmentText": text,
        }
        return make_response(jsonify(reply))
    elif action == 'edit_order':  # edit order
        text = edit_order()
        reply = {
            "fulfillmentText": text,
        }
        return make_response(jsonify(reply))
    elif action == 'edit_details':  # edit individual detail
        text = edit_details()
        reply = {
            "fulfillmentText": text,
        }
        return make_response(jsonify(reply))
    elif action == 'stop_order':  # check phone
        text = check_phone()
        reply = {
            "fulfillmentText": text,
        }
        return make_response(jsonify(reply))
    elif action == 'check_passcode':  # check phone
        text = check_pwd()
        reply = {
            "fulfillmentText": text,
        }
        return make_response(jsonify(reply))
    elif action == 'get_passcode':  # check phone
        text = add_pwd()
        reply = {
            "fulfillmentText": text,
        }
        return make_response(jsonify(reply))
    elif action == 'mode':  # check phone
        text = add_mode()
        reply = {
            "fulfillmentText": text,
        }
        return make_response(jsonify(reply))


if __name__ == '__main__':
    app.run()
