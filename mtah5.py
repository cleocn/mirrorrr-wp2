# coding=utf8
#!/usr/bin/env python
import requests
import md5
import logging
import json

class MtaH5():
	def __init__(self):
		self.APP_ID = "500324497"
		return

	def getsig(self,params):
		SECRET_KEY  =  '9f5651e3c23bb172cec3630874034ac7'
		# logging.debug("sig:",params)
		for key in sorted(params):
			SECRET_KEY += '%s=%s'%(key,params[key])
		m = md5.new()
		m.update(SECRET_KEY)
		sign = m.hexdigest()
		return sign

	def req(self,api,params):
		params.update({"app_id":self.APP_ID})
		params.update({"sign":self.getsig(params)})
		response = requests.post(api,data=params)
		return response.content

	def api(self,req_params):
		params = {}
		for key in req_params:
			params.update({key:req_params[key]})
		# logging.debug("api:",params)
		api = "http://mta.qq.com/h5/api/%s"%params["api"]
		del params["api"]
		params.update({"app_id":self.APP_ID})
		params.update({"sign":self.getsig(params)})
		response = requests.post(api,data=params)
		return response.content

	#http://mta.qq.com/h5/api/ctr_page
	# app_id 		#整数 		# 应用ID 	# 应用注册时生成的ID。
	# start_date 	# 字符串 	# 开始时间 	# 开始时间(Y-m-d)
	# end_date		# 字符串	# 结束时间	# 结束时间(Y-m-d)
	# urls	字符串	url地址 	# url地址，多个使用逗号“,”间隔，必须经过url编码
	# idx	# 字符串	# 指标列表	# 可选值详见附录（指标字典），使用“,”间隔查询指标
	# sign	# 字符串	# 验证串	# 见示例生成过程
	def ctr_page(self,urls):		
		api = "http://mta.qq.com/h5/api/ctr_page"
		params = {			
			"start_date":"2015-10-24",
			"end_date":"2016-10-25",
			"urls":urls,
			"idx":"pv,uv,vv,iv",
			}		
		return self.req(api,params)

	# http://mta.qq.com/h5/api/ctr_core_data
	def ctr_core_data(self):		
		api = "http://mta.qq.com/h5/api/ctr_core_data"
		params = {
			"start_date":"2015-10-24",
			"end_date":"2016-10-25",
			"idx":"pv,uv,vv,iv",
			}
		return self.req(api,params)
