# Copyright (C) 2010, Thomas Leonard
# Visit http://0install.net for details.

from zeroinstall.injector import iface_cache

def format_combo(combo):
	this_combo = []
	for iface, version in combo.iteritems():
		this_combo.append("%s v%s" % (iface.get_name(), version))
	return ', '.join(this_combo)

def print_summary(results):
	print "\nSUMMARY:\n"

	for label in ["passed", "skipped", "failed"]:
		results_for_status = results.by_status[label]
		if not results_for_status:
			print "None", label
		else:
			print label.capitalize()
			for combo in results_for_status:
				print " - " + format_combo(combo)

def format_html(results):
	spec = results.spec

	from xml.dom import minidom
	impl = minidom.getDOMImplementation()
	doctype = impl.createDocumentType("html",
			"-//W3C//DTD XHTML 1.0 Strict//EN",
			"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd")
	XMLNS_XHTML = "http://www.w3.org/1999/xhtml"
	doc = impl.createDocument(XMLNS_XHTML, "html", doctype)
	root = doc.documentElement

	head = doc.createElement('head')
	root.appendChild(head)
	title = doc.createElement('title')
	title.appendChild(doc.createTextNode('0test results for ' + spec.test_iface))
	head.appendChild(title)
	style = doc.createElement('style')
	head.appendChild(style)
	style.setAttribute('type', "text/css")
	style.appendChild(doc.createTextNode("""
		table.testresults {
			border: 1px solid black;
			background: white;
			color: white;
		}

		table.testresults th {
			text-align: left;
			background: #888;
		}

		table.testresults td.passed {
			white-space: pre;
		}

		table.testresults td.passed {
			background: green;
		}

		table.testresults td.skipped {
			background: yellow;
			color: #888;
		}

		table.testresults td.failed {
			background: red;
		}
	"""))

	body = doc.createElement('body')
	root.appendChild(body)

	for outer_combo in spec.get_combos(spec.test_ifaces[:-2]):
		outer_key = frozenset(outer_combo.items())
		outers = [(iface_cache.iface_cache.get_feed(uri).get_name() + " " + version) for (uri, version) in outer_combo.iteritems()]

		heading = doc.createElement('h1')
		heading.appendChild(doc.createTextNode(', '.join(outers) or 'Results'))
		body.appendChild(heading)

		table = doc.createElement('table')
		table.setAttribute('class', 'testresults')
		body.appendChild(table)

		col_iface_uri = spec.test_ifaces[-1]
		row_iface_uri = spec.test_ifaces[-2]

		col_iface = iface_cache.iface_cache.get_interface(col_iface_uri)
		row_iface = iface_cache.iface_cache.get_interface(row_iface_uri)

		test_columns = spec.test_matrix[spec.test_ifaces[-1]]

		row = doc.createElement('tr')
		table.appendChild(row)
		th = doc.createElement('th')
		row.appendChild(th)
		th = doc.createElement('th')
		th.setAttribute("colspan", str(len(test_columns)))
		row.appendChild(th)
		th.appendChild(doc.createTextNode(col_iface.get_name()))

		row = doc.createElement('tr')
		table.appendChild(row)
		th = doc.createElement('th')
		row.appendChild(th)
		th.appendChild(doc.createTextNode(row_iface.get_name()))
		for col_iface_version in spec.test_matrix[col_iface_uri]:
			th = doc.createElement('th')
			row.appendChild(th)
			th.appendChild(doc.createTextNode(col_iface_version))

		for row_iface_version in spec.test_matrix[row_iface_uri]:
			table.appendChild(doc.createTextNode('\n'))
			row = doc.createElement('tr')
			table.appendChild(row)
			th = doc.createElement('th')
			row.appendChild(th)
			th.appendChild(doc.createTextNode(row_iface_version))
			for col_iface_version in test_columns:
				td = doc.createElement('td')
				row.appendChild(td)
				key = frozenset(outer_key | set([(row_iface_uri, row_iface_version), (col_iface_uri, col_iface_version)]))

				result, selections = results.by_combo[key]
				td.setAttribute('class', result)

				other_ifaces = []
				combo_ifaces = set(uri for (uri, version) in key)
				for iface, version in selections.iteritems():
					if iface.uri not in combo_ifaces:
						other_ifaces.append((iface.get_name(), version))
				if other_ifaces:
					td.appendChild(doc.createTextNode('\n'.join('%s %s' % (uri, version) for uri, version in other_ifaces)))
				else:
					td.appendChild(doc.createTextNode(result))
		table.appendChild(doc.createTextNode('\n'))

	return doc
