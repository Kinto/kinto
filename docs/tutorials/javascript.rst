.. _tutorial-javascript:

Kinto for JavaScript applications
#################################

Kinto is particularly relevant for the Web, thus it is very probable that you'll
want to interact with the server using JavaScript.

This tutorial presents the basics, but you can look at
:ref:`the applications examples <app-examples>`, most of them use JavaScript.


Offline and synchronization
---------------------------

We built :github:`kinto.js <Kinto/kinto.js>`, a JavaScript client dedicated
to synchronizing remote records with a local database.

The best way to start is :rtd:`to follow the dedicated tutorial <kintojs>` !

Using an offline-first client is not mandatory, see the following section for
a tutorial using «*vanilla JS*».


Using the standard Fetch API
----------------------------

First, let's define some constants that will hold very basic information for
our script:

.. code-block:: javascript

    // Mozilla demo server
    var server = "https://kinto.dev.mozaws.net/v1";

    // Kinto bucket/collection.
    var bucket = "blog";
    var collection = "articles";

    // Endpoints URLs
    var bucketURL = `${server}/buckets/${bucket}`;
    var collectionURL = `${bucketURL}/collections/${collection}`;
    var recordsURL = `${collectionURL}/records`;


For the sake of simplicity, let's use Basic Authentication:

.. code-block:: javascript

    // Simplest credentials ever.
    var authorization =  "Basic " + btoa("public:notsecret");

    // Resuable HTTP headers.
    var headers = {
      "Accept":        "application/json",
      "Content-Type":  "application/json",
      "Authorization": authorization,
    };
    var options = {headers: headers};


We will create the bucket and the collection, only if they don't exist, using
a ``PUT`` request and headers for :ref:`concurrency control <api-concurrency-control>`:

.. code-block:: javascript

    var putHeaders = Object.assign({"If-None-Match": "*"}, headers);
    var putOptions = {method: "PUT", headers: putHeaders};

    fetch(bucketURL, putOptions)
      .then(function (response) {
        return fetch(collectionURL, putOptions);
       });

Now, we are able to create some records:

.. code-block:: javascript

    var data = {title: "How Kinto changed my life", date: new Date().toISOString()};
    var body = JSON.stringify({data: data});
    var postOptions = Object.assign({method: "POST", body: body}, options);

    fetch(recordsURL, postOptions)
      .then(function (response) {
        return response.json();
      })
      .then(function (result) {
        console.log('Created record with id=', result.data.id);
      });

And of course retrieve them:

.. code-block:: javascript

    fetch(recordsURL, options)
      .then(function (response) {
        return response.json();
      })
      .then(function (result) {
        console.log(result.data.length, ' records found.');
      });

In order to :ref:`poll for changes <api-synchronisation>`, store the last
synchronization timestamp, and reuse it:


.. code-block:: javascript

    var url = `recordsURL?_since=${timestamp}`;
    fetch(url, options)
      .then(function (response) {
        // Store timestamp for next run.
        timestamp = response.headers['ETag'];
        // If nothing changed, response body is empty.
        if (response.status == 304) {
            console.log('Nothing changed.');
            return {data: []};
        }
        return response.json();
      })
      .then(function (result) {
        result.data.forEach(function (record) {
            if (record.deleted) {
                console.log('Deleted record id=', record.id);
            }
            else {
                console.log('New record id=', record.id);
            }
        });
      });
