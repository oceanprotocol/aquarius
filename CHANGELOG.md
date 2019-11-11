History
=======


0.4.2 (Aug 29th, 2019)
----------------------
* Fix to allow new ddos schemas

0.4.1 (Aug 16th, 2019)
----------------------
* Change serviceDefinitionId to index
* Type of services have to be lowercase

0.4.0 (Aug 13th, 2019)
----------------------
* Update to the new DDO structure with main instead of base.
* OEP7 changes (https://github.com/oceanprotocol/OEPs/tree/master/7/v0.2)
* OEP8 changes(https://github.com/oceanprotocol/OEPs/tree/master/8/v0.4)

0.3.8 (Jul 16th, 2019)
----------------------
* Fix search by type.

0.3.7 (Jul 3rd, 2019)
----------------------
* Add health check endpoint.

0.3.6 (Jul 2nd, 2019)
----------------------
* Retry connection when elastic is not up.
* Move mapping when elastic start.

0.3.5 (June 28st, 2019)
----------------------
* Create mapping for elastic plugin.
* Update swagger doc.

0.3.4 (June 26st, 2019)
----------------------
* Allow free asset only for commons marketplaces.

0.3.3 (June 21st, 2019)
----------------------
* Fix bug text query in elastic

0.3.2 (June 20th, 2019)
----------------------
* Support datePublished and dateCreated queries in elastic.

0.3.1 (June 13th, 2019)
----------------------
* Not change serviceDefinitionId when reordering the metadata.

0.3.0 (June 12th, 2019)
----------------------
* Reorder services to have the metadata the first in the array.
* Small bugs and upgrade of plugins.

0.2.9 (June 4th, 2019)
----------------------
* Return errors when parameters are not ok.

0.2.8 (May 31st, 2019)
----------------------
* Fix small bugs.

0.2.7 (May 28th, 2019)
----------------------
* Update plecos version

0.2.6 (May 24th, 2019)
----------------------
* Update elasticsearch plugin

0.2.5 (May 22nd, 2019)
----------------------
* Fix error related with the ddo version.

0.2.4 (May 22nd, 2019)
----------------------
* Fix bug in the condition price type.

0.2.3 (May 20th, 2019)
----------------------
* Save price as a String.

0.2.2 (April 9th, 2019)
----------------------
* Fix bug in search queries.

0.2.1 (April 5th, 2019)
-----------------------
Add the pagination in the search queries.

0.2.0 (March 29th, 2019)
------------------------
* Include datePublished in the base following the changes in OEP8.
* Plecos version 0.7.0

0.1.11 (March 14th, 2019)
-------------------------
* Bugfix for curation attribute handling
* Latest Plecos, OEP8 v0.1

0.1.10 (February 27th, 2019)
-------------------------
* Add /validate endpoint.

0.1.9 (February 21st, 2019)
-------------------------
* Support of custom queries.

0.1.8 (February 1st, 2019)
-------------------------
* Checksum requirement

0.1.7 (January 30th, 2019)
-------------------------
* Change files to encyptedFiles

0.1.6 (January 29th, 2019)
-------------------------
* Updated with the changes in the OEP-8

0.1.5 (January 17th, 2019)
-------------------------
* Compatibility:
    - squid-py 0.2.22
    - keeper-contracts 0.5.3
    - brizo 0.1.5

0.1.4 (November 16th, 2018)
-------------------------
* Minor bugs fixed.

0.1.3 (November 14th, 2018)
-------------------------
* Fix issue returning string instead of objects.

0.1.2 (November 5th, 2018)
-------------------------
* First release after the split of the provider into aquarius and brizo components.
* Aquarius content all the endpoints to be able to interact with oceanDB.

0.1.1 (October 17th, 2018)
-------------------------
* Integration with squid-py.
* Search capabilities in bigchaindb, mongodb and elasticsearch.

0.1.0 (August 15th, 2018)
-------------------------
* Plankton release
