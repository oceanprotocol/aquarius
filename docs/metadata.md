# Metadata of data assets

Each data asset must have a metadata struct associated with it. 
This metadata is stored in the oceandb and can be accessed using the assetId.
Data assets without proper descriptive metadata can have poor visibility and discoverability.

## Required metadata
* Name/Title: a few words describing the resource.
* Links: links for data samples, or links to find out more information
* Size: size of data in MB, GB, or Tera bytes
* Format: file format if applicable
* Description: details of what the resource is. For a data set explain what the data represents and what it can be used for.

## Optional metadata
These are examples of attributes that can enhance the discoverability of a resource:

* License
* Service level agreement
* Date: date the resource was made available
* Labels: labels can serve the role of multiple categories
* Keywords: can enhance search and find functions
* Classification: need examples here
* Industry: self-explanatory
* Category: can be assigned to a category in addition to having labels
* Note: any additional information worthy of highlighting (description maybe sufficient)
* Update frequency: how often are updates expected (seldome, annual, quarterly, etc.), or is the resource static (never expected to get updated)
* Life cycle state: ?

## Future considerations
`Some of these may actually need to be required attributes.`

Privacy

License:
* Public Domain
* Creative Commons Public Domain Dedication
* ... there is a long list of license types here: https://help.data.world/hc/en-us/articles/115006114287-Common-license-types-for-datasets 

Service level agreement

Terms of service
