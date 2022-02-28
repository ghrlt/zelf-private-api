import re
import json
import base64
import requests


class PhoneNumber:
	def __init__(self, num: str):
		self.num = num
		self.checkIfValid()

	def checkIfValid(self):
		# Open to better/more efficient checking ways - Fill a PR

		n = self.num
		assert n[0] == "+", "It seems that the phone indicatif was not provided!"
		assert len(n) in [12,13,14], "It seems that the provided phone number is not valid!"

		if n[1:3] in [32, 33, 34]:
			assert n[4] in [6,7] or n[5] in [6,7], "Looks like your phone number is not a mobile one!"



class Zelf:
	API_HOST = "https://i.zelf.co"

	def __init__(self):
		self.s = requests.Session()
		self.s.headers = {
			"accept": "application/json",
			"accept-charset": "UTF-8",
			"content-type": "application/json",
			"host": "i.zelf.co",
			"user-agent": "Ktor client" # Unable to change..
		}

	def login(self, phone_number: PhoneNumber, otp_code: int=None) -> bool:
		PhoneNumber(phone_number)

		if otp_code is None: #aka login request
			r = self.s.post(
				self.API_HOST+"/auth/api/v1/registration",
				json={"cell_phone": phone_number, "channel": "Mobile"}
			).json()

			if r.get('confirmation_method') is None:
				err = r.get('type') + " – " + r.get('client_message')
				err += " Retry in " + str(r.get('retry_in') or r.get('extra_fields').get('retry_in'))
				return err, print(err)
		
			elif r.get('confirmation_method') == "OtpSms": #No other confirmation methods, yet?
				self.s.headers['x-confirmation-token'] = r['confirmation_token']
				self.retry_in_minimum = r.get('retry_in')

				return self.login(phone_number, otp_code=input("Login code (Sent by sms to your number): "))


		else: #aka login confirmation
			headers = self.s.headers
			headers['x-confirmation-code'] = otp_code

			r = self.s.put(
				self.API_HOST+"https://i.zelf.co/auth/api/v1/registration",
				json={"cell_phone": phone_number, "channel": "Mobile"},
				headers=headers
			).json()

			if not r.get("state") == "Complete":
				err = r.get("type") + " – " + r.get("client_message")
				return err, print(err)


			self.s.headers['cookie'] = "Authorization="+self.s.headers['x-confirmation-token']
			del self.s.headers['x-confirmation-token']

			r_test = self.s.get(self.API_HOST+"/sme/api/v1/customers/retail")
			if r_test.status_code == 200:
				return True, print("Successfully logged in")
			return False, print("Unable to login")

	def force_login(self, authorization_token: str) -> bool:
		self.s.headers['cookie'] = "Authorization="+authorization_token

		r_test = self.s.get(self.API_HOST+"/sme/api/v1/customers/retail")
		if r_test.status_code == 200:
			return True, print("Successfully logged in")
		return False, print("Unable to login using this auth token")


	def getAccountDetails(self) -> dict:
		r = self.s.get(self.API_HOST+"/sme/api/v1/customers/retail").json()

		self.account = {
			"id": r['customer_id'],
			"referral_id": r['referral_uid'],
			"state": r['state'],
			"type": r['customer_type'],
			"is_verified": False if r['identification_level'] == "NotIdentified" else True,
			"is_deleted": r['is_deleted'],
			"has_card": r['is_card_available'],
			"has_confirmed_phone": r['is_phone_confirmed'],
			"has_accepted_terms": r['accepted_terms'],
			"is_junior": r['has_junior_program'],
			"avatar": r['avatar_url'],
			"user": {
				"firstname": r['person']['person_name']['first_name'],
				"middlename": r['person']['person_name']['middle_name'],
				"lastname": r['person']['person_name']['last_name'],
				"gender": r['person']['gender'],
			},
			"achievements": r['achievements']
		}
		if self.account['is_junior'] is True:
			self.account['parent_id'] = r['parent_customer_id']
		
		if self.account['is_verified'] is True:
			self.account['user']['martial_status']: r['person']['martial_status'] #typo? might be marital | To watch
			self.account['user']['residence_country_code'] = r['person']['residence_country_code']
			self.account['user']['birth_infos'] = {
				"birth_date": r['person']['birth_date'],
				"birth_country": r['person']['birth_country'],
				"birth_place": r['person']['birth_place'],
			}

		return self.account

	def getCardsInfos(self) -> dict:
		r = self.s.get(self.API_HOST+"/sme/api/v1/cards").json()

		self.cards = []
		for card in r:
			self.cards.append(
				{
					"id": card['id'],
					"is_active": True if card['status'] == "Active" else False,
					"currency": card['currency'],
					"owner": card['embossed_name'],
					"striked_card_number": card['masked_card_number'],
					"created_on": card['open_date'],
					"balance": card['balance']['value']
				}
			)

		return self.cards

	def getBonusDetails(self) -> dict:
		r = self.s.get(self.API_HOST+"/sme/api/v1/bonusaccounts").json()

		self.bonuses = r

		return self.bonuses

	def getCardDetails(self, card_id: int) -> dict:
		r = self.s.get(self.API_HOST+f"/sme/api/v1/cards/{card_id}/requisites").json()

		for i in range(len(self.cards)):
			if self.cards[i]['id'] == card_id:
				break

		self.cards[i]['clear_number'] = base64.b64decode(r['number']).decode('utf-8')
		self.cards[i]['expiration_date'] = r['expiry_date']

		r = self.s.get(self.API_HOST+f"/sme/api/v1/cards/{card_id}/cvc").json()
		self.cards[i]['cvv'] = base64.b64decode(r['cvc']).decode('utf-8')

		return self.cards[i]

	def getIbanInfos(self):
		r = self.s.get(self.API_HOST+"/sme/api/v1/cards/topup/iban").json()

		self.iban = r
		return r

	def getLimitsInfos(self) -> dict:
		r = self.s.get(self.API_HOST+"/sme/api/v1/limits").json()

		self.limits = {
			"spending": {
				"spent": r['spending']['period_30_days']['current_amount']['value'],
				"limit": r['spending']['period_30_days']['limit_amount']['value'],
			},
			"topup": {
				"topped_up": r['topup']['period_30_days']['current_amount']['value'],
				"limit": r['topup']['period_30_days']['limit_amount']['value']
			}
		}
		self.limits['spending']['left'] = self.limits['spending']['limit']-self.limits['spending']['spent']
		self.limits['topup']['left'] = self.limits['topup']['limit']-self.limits['topup']['topped_up']

		return self.limits


	def getCardTopupLink(self, card_id: int) -> str:
		r = self.s.get(self.API_HOST+f"/sme/api/v1/cards/{card_id}/hipay-link").json()

		return r.get('url')


z = Zelf()
login_result = z.force_login(open("authtoken", "r").read())
if type(login_result) == tuple and login_result[0] is False:
	z.login(input("Your ZELF account phone number: "))


print( z.getCardDetails(z.getCardsInfos()[0]['id']) )
print( z.getAccountDetails() )
print( z.getCardTopupLink(z.cards[0]['id']) )
print( z.getIbanInfos() )