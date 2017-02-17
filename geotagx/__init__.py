# -*- coding: utf-8 -*-
#
# This module is part of the GeoTag-X PyBossa plugin.
#
# Author: Jeremy Othieno (j.othieno@gmail.com)
#
# Copyright (c) 2017 UNITAR/UNOSAT
#
# The MIT License (MIT)
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.
from flask.ext.plugins import Plugin

__plugin__  = "GeoTagX"
__version__ = "0.0.1"


class GeoTagX(Plugin):
    def setup(self):
        """Initializes the GeoTag-X plugin.
        """
        from flask import current_app as app
        from view.admin import blueprint as admin_blueprint
        from view.blog import blueprint as blog_blueprint
        from view.community import blueprint as community_blueprint
        from filters import blueprint as filter_blueprint
        from view.geojson_exporter import blueprint as geojson_exporter_blueprint
        from view.feedback import blueprint as feedback_blueprint
        from view.geotagx import blueprint as geotagx_blueprint
        from view.survey import blueprint as survey_blueprint

        # The plugin's default configuration.
        default_configuration = {
            "GEOTAGX_NEWSLETTER_DEBUG_EMAIL_LIST": [],
        }
        for key in default_configuration:
            if app.config.get(key, None) is None:
                app.config[key] = default_configuration[key]

        # A list of blueprint <handle, URL prefix> pairs.
        blueprints = [
            (admin_blueprint, "/admin"),
            (blog_blueprint, "/blog"),
            (community_blueprint, "/community"),
            (filter_blueprint, None),
            (feedback_blueprint, "/feedback"),
            (geojson_exporter_blueprint, None),
            (geotagx_blueprint, "/geotagx"),
        ]
        for (handle, url_prefix) in blueprints:
            app.register_blueprint(handle, url_prefix=url_prefix)

        setup_project_categories()
        setup_views(app)

        setup_survey(app)
        setup_sourcerer(app)
        setup_helper_functions(app)


def setup_default_configuration(app, default_configuration):
    """Sets up the specified application's default configuration.

    This function will only modify an application's configuration entry
    if it does not already contain a value.

    Args:
        app (werkzeug.local.LocalProxy): The application's instance.
        default_configuration (dict): The default configuration.
    """
    if default_configuration and isinstance(default_configuration, dict):
        for key in default_configuration:
            if app.config.get(key, None) is None:
                app.config[key] = default_configuration[key]


def setup_views(application):
    """Sets up the plugin's views.

    Args:
        application (werkzeug.local.LocalProxy): The current Flask application's instance.
    """
    from view.project_browser import setup as project_browser_setup
    for setup in [
        project_browser_setup,
    ]: setup(application)


def setup_survey(app, url_prefix="/survey"):
    """Sets up the participation survey.

    Args:
        app (werkzeug.local.LocalProxy): The current application's instance.
        url_prefix (str): The blueprint's URL prefix.
    """
    from view.survey import blueprint

    setup_default_configuration(app, {
        "GEOTAGX_FINAL_SURVEY_TASK_REQUIREMENTS": 30,
    })
    app.register_blueprint(blueprint, url_prefix=url_prefix)


def setup_sourcerer(app, url_prefix="/sourcerer"):
    """Sets up the sourcerer.

    Args:
        app (werkzeug.local.LocalProxy): The current application's instance.
        url_prefix (str): The blueprint's URL prefix.
    """
    from view.sourcerer import blueprint

    app.register_blueprint(blueprint, url_prefix=url_prefix)


def setup_helper_functions(app):
    """Sets up the helper functions.

    Args:
        app (werkzeug.local.LocalProxy): The current application's instance.
    """
    import helper
    functions = {
        "get_project_category": helper.get_project_category,
        "get_blurred_cover_image_path": helper.get_blurred_cover_image_path,
    }
    app.jinja_env.globals.update(**functions)


def setup_project_categories():
    """Sets up the default project categories.
    """
    from pybossa.core import project_repo
    from pybossa.model.category import Category
    from pybossa.cache import categories as category_cache

    # TODO Move category information to a data file (e.g. a markdown file) that can be easily edited.

    categories = [
        Category(
            name="Somali Drought",
            short_name="somalidrought",
            description=u"""This project investigates what information about drought symptoms can be associated with photos.  <br> Images in this project come from <a href="http://www.faoswalim.org/">FAO SWALIM</a> on <a href="https://secure.flickr.com/photos/faoswalim/sets/72157642992734333/">Flickr</a>.  <br> Please <a href="https://github.com/geotagx/pybossa/issues">share your feedback</a> on the modules in this project.   <br> This pilot was codeveloped with Lauren Young (Arcadia Center for Sustainable Food and Agriculture), Ilya Fischhoff, Sarah Green (Michigan Tech), and Tom Sappington (USDA-ARS).  <br><br> This work is licensed <a href="http://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0</a>. This page was last updated 21 October 2014.
            """
        ),
        Category(
            name="Yamuna Monsoon Flooding 2013",
            short_name="yamunamonsoonflooding2013",
            description=u"""The Yamuna River is dying from industrial pollution and untreated sewage. With more than 75,000 people living on the riverbanks of the Yamuna, the persistent emergency of river pollution can turn into an acute crisis during monsoonal flooding when large numbers of poor people in marginalised riverside communities can be exposed to extremely polluted floodwater. We hope that citizen-generated images and analyses of those images can document the gravity of the river pollution, its interaction with the seasonal monsoon flooding, its multiple adverse effects on communities and the urgency for environmental restoration of the river.<p></p>    <p><a href="http://www.thehindu.com/news/cities/Delhi/lowlying-areas-along-yamuna-in-delhi-flooded/article4832814.ece">The 2013 monsoon floods </a> were some of the most severe on record with some 5000 people being evacuated into relief camps. Watch <a href="http://www.ndtv.com/video/player/news/yamuna-breaches-danger-mark-in-delhi/279650">the video</a> for more context. This pilot project is using images from the 2013 event as a test case. Contributors are helping us to test and improve Geotag-X modules about Yamuna flooding for use during future monsoon seasons. You are also welcome to contribute and to learn more about life on the Yamuna River. The eventual aim is for crowd-sourced photographic image analysis to complement existing disaster response and recovery efforts, such as analysis of <a href="http://www.un-spider.org/sites/default/files/IND-modis_floodinundation_22June2013.pdf">satellite images</a> and field assessments.</p>   <p>Yamuna Monsoon Flooding is a Geotag-X pilot project, co-developed in 2014 with Dr Sylvia Nagl of <a href="http://yamuna.womenforsustainablecities.org/">Yamuna's Daughters</a> and Dr <a href="http://tecfa.unige.ch/perso/rosita/-/Home.html">Rosita Haddad-Zubel</a>. Yamuna's Daughters is a photography project for teenage girls living along New Delhi’s <a href="http://en.wikipedia.org/wiki/Yamuna">Yamuna River</a>, which is the lifeline of the city’s water supply. </p>    <br> “ २०१३ यमुना मानसून बाढ़ ” यमुना की बेटियों की डॉ. सिल्विया नागल  और  डॉ. रोसिता हद्दाद-जुब्बल सह विकसित पहला जिओटैग-एक्स  प्राथमिक परियोजना है | यमुना की बेटियों शहर के पानी की आपूर्ति की जीवन रेखा है जो नई दिल्ली के यमुना नदी के साथ रहने वाले किशोर लड़कियों के लिए एक फोटोग्राफी परियोजना है.  नई दिल्ली में नागरिक फोटोग्राफरों सहित इस प्राथमिक परियोजना के लिए योगदानकर्ता, हमें भविष्य के मानसून सीजन के दौरान इस्तेमाल के लिए यमुना में बाढ़ के बारे में जिओटैग-एक्स मॉड्यूल का परीक्षण करने और बेहतर बनाने में मदद कर रहे हैं | आप भी योगदान करने के लिए और यमुना नदी पर जीवन के बारे में अधिक जानने के लिए स्वागत है | इन क्राउड-सौरसेड छवि विश्लेषण इस तरह के उपग्रह चित्रों और क्षेत्र के मूल्यांकन के विश्लेषण के रूप में मौजूदा आपदा प्रतिक्रिया और वसूली प्रयासों, पूरक करने के लिए उद्देश्य है |  ७५००० से अधिक लोग यमुना, इतिहास में कई विनाशकारी बाढ़ की एक साइट की नदी के किनारे पर रहते हैं | २०१३ बाढ़ निवासियों को खाली और बुनियादी ढांचे की रक्षा करने के लिए स्थानीय स्तर पर उपलब्ध बचाव और राहत उपायों के सभी शामिल किया गया | हम चाहते हैं कि क्राउड-सौरसेड फोटो विश्लेषण भविष्य बाढ़ की स्थिति में आपदा प्रतिक्रियाओं सहायता कर सकता है उम्मीद है |  <br> Translation from English to Hindi by S.P. Mohanty. <br>    <br> <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-sa/4.0/88x31.png"></a><br>This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>. <br> <p>Latest version published 04/09/2014. </p>
            """
        ),
#        Category(
#            name="Yemeni Agricultural Water Assessment",
#            short_name="yemeniagriculturalwaterassessment",
#            description=u"""This module was created for UNOSAT's assistance to the international relief agency <a href="http://www.acted.org">ACTED</a>, in mapping agricultural areas of the Raymah division of Yemen to help improve water use.  <br><br> Much of this work has been done with satellite imagery, but photographs or videos of agricultural areas and practices in or near the Raymah division of Yemen were also valuable.  <br><br> Right now this project has few images, so if you have seen relevant media, you can <a href="http://geotagx.org/find_photos">use the Geotag-X firefox plugin</a> to share relevant media.  <br><br> Local knowledge of Raymah is valuable for geotagging this module.  <br><br> Media about coffee or qat (also spelt khat) crops in the area are particularly relevant, as well as any assessment of soil conditions or drought stress. This PDF <a href="http://reliefweb.int/sites/reliefweb.int/files/resources/REACH_coffee_value_chain_assessment_in_Raymah_governorate_Yemen.pdf"> report about coffee production</a> is a related research outcome. <br><br> The icon for this module is from <a href="http://www.unocha.org/">UNOCHA</a> via <a href="”https://commons.wikimedia.org/wiki/File:Yemen_-_Location_Map_(2013)_-_YEM_-_UNOCHA.svg”">Wikimedia Commons.</a> <br><br> This module uses OpenStreetMap and therefore the <a href="http://www.openstreetmap.org/copyright">Open Database License</a>.  <br><br> Latest version of this text was published on 09/09/2014.
#            """
#        ),
        Category(
            name="Ebola response",
            short_name="ebolaresponse",
            description=u"""Assessing use of personal protective equipment in ebola response efforts. The WHO has <a href="http://www.who.int/csr/resources/publications/ebola/filovirus_infection_control/en/">new protective equipment guidelines</a> in response to the Ebola crisis. Here is a <a href="http://www.who.int/csr/disease/ebola/put_on_ppequipment.pdf"> PDF showing steps to putting on protective equipment</a>. Since there is no known cure for Ebola, protection from infection is crucial in emergency response. <a href="http://www.cdc.gov/media/releases/2014/fs1020-ebola-personal-protective-equipment.html">Changes to this guidance in response to Ebola are explained by the CDC</a>. <br><br> This module is part of the <a href="http://citizencyberlab.eu">Citizen Cyberlab project researching citizen science</a>. It aims to raise awareness of Ebola emergency response efforts and to experiment with using GeoTag-X to support training about personal protective equipment. Results are experimental and do not directly contribute to Ebola response action. <b>The UN has created the first-ever UN emergency health mission for this crisis that includes <a href="http://www.un.org/ebolaresponse/needs.shtml">a list of what is still needed</a>. If you can contribute to emergency needs listed by UNMEER, please focus your efforts there first. </b> <br><br> If you have time to contribute to our research by completing this module, please share your feedback preferably <a href="https://github.com/geotagx/pybossa/issues">on GitHub</a>, or <a href="https://etherpad.mozilla.org/geotagx"> on Etherpad without logging in</a>.  <br><br> Images to begin this project are from <a href="https://secure.flickr.com/photos/126392347@N06/">from Médecins Sans Frontières Australia</a>, <a href="https://secure.flickr.com/photos/unicefliberia/sets/72157645220442480/">UNICEF Liberia</a> and the <a href="https://secure.flickr.com/people/ifrc/">International Federation of Red Cross and Red Crescent Societies</a>. Click the 'view photo source' button below an image to check the license.  <br><br> This project is licensed <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike</a> and the <a href="https://github.com/geotagx">code is open</a>.  <br><br> Developed by Cobi Smith in association with the <a href="http://home.web.cern.ch/about/updates/2014/11/unosat-joins-fight-against-ebola">UNITAR-UNOSAT Ebola response</a>.  <br><br> Last updated 4 November 2014.
            """
        ),
        Category(
            name="Emergency Shelter Assessment in the Middle East",
            short_name="emergencyshelterassessmentinthemiddleeast",
            description=u"""This project is about assessing the suitability of emergency shelter, by answering simple questions about a series of photographs. These are observation questions, which are used to understand people’s needs and vulnerabilities. The answers to needs assessment questions like this help local people, governments, and humanitarian actors plan an emergency response.
            """
        ),
        Category(
            name="Under Development",
            short_name="underdevelopment",
            description=u"These projects are under development"
        ),
    ]

    # Filter out any existing categories.
    EXISTING_CATEGORY_SHORT_NAMES = {c.short_name for c in category_cache.get_all()}
    categories = filter(lambda c: c.short_name not in EXISTING_CATEGORY_SHORT_NAMES, categories)

    if categories:
        for category in categories:
            project_repo.save_category(category)

        category_cache.reset()
