from set_up import qgc
from lxml.builder import E
from lxml import objectify
from xml.sax.saxutils import escape

# returns int webapp count


def webapp_count(tag):
    """
    gets number of web applications assigned to a tag

    Parameters
    ----------
    tag : str
        stakeholder tag

    Returns
    -------
    webapp count : int
        number of webapps
    """
    ENDPOINT = "count/was/webapp"
    req = (
        E.ServiceRequest(
            E.filters(
                E.Criteria(tag, field="tags.name", operator="EQUALS")
            )
        )
    )
    xml_output = qgc.request(ENDPOINT, req)
    root = objectify.fromstring(xml_output.encode())
    return int(root.count)


def delete_webapp(app):
    """
    deletes a webapp

    Parameters
    ----------
    app : str
        url of the web application to be deleted
    """
    # removes webapp from subscription
    ENDPOINT = "/delete/was/webapp"

    safe_app = escape(app, {'"': '&quot;', "'": '&apos;'})

    post = '''<ServiceRequest>
        <filters>
        <Criteria field="url" operator="EQUALS">%s</Criteria>
        </filters>
        <data>
        <WebApp>
        <removeFromSubscription>true</removeFromSubscription>
        </WebApp>
        </data>
        </ServiceRequest>''' % safe_app

    response = qgc.request(ENDPOINT, post, http_method='POST')
    root = objectify.fromstring(response.encode())
    print("Status on app deletion for %s: %s" % (app, root.responseCode))
