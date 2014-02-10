import os
import webapp2
import jinja2

""" BaseHandler webapp2 RequestHandler class definition """
class BaseHandler(webapp2.RequestHandler):
	def render_template(self, file, template_args):
		JINJA_ENVIRONMENT = jinja2.Environment(
										   loader=jinja2.FileSystemLoader(os.path.dirname(__file__)+'/templates'),
										   extensions=['jinja2.ext.autoescape'],
										   autoescape=True)
		template = JINJA_ENVIRONMENT.get_template(file)
		self.response.write(template.render(template_args))


