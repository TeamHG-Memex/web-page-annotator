Web Page Annotator
==================

This is a small web application for muli-class annotation of elements on web pages.

Workflow:

- Create a workspace: specify labels (classes you want to use)
  and URLs which you want to label.
- On each page, hover over the element you want to label,
  do a right-click and choose the label.
- When done labeling the page, press "Next" to go to the next page.
- You can edit URLs or labels in the current workspace at any time by clicking
  the "Workspace" button.
- To get you labeling results and pages saved for offline viewing/rendering,
  click the "Export" button.

How this works: pages are rendered in an iframe and proxied through the local server.
This allows to intercept all requests to resources and save them,
and we can communicate with an iframe because it is coming from the same domain.
Data is stored in an sqlite database.

Installation::

    pip install -r requirements.txt


Usage::

    ./app.py


License is MIT.

----

.. image:: https://hyperiongray.s3.amazonaws.com/define-hg.svg
	:target: https://www.hyperiongray.com/?pk_campaign=github&pk_kwd=web-page-annotator
	:alt: define hyperiongray
