# Challenges

[Table of Contents](toc.md)

The ActivityPub specification seems easy to implement when one first skims the document. However, it eventually because apparent that there is a lot of complexity involved in developing a non-toy server.

This complexity (whether accidental or not) is a challenge for testing too.

## Underspecified ActivityPub Specification

There are many requirements that are open to interpretation or allow behaviors that are don't appear to be consistent with the spirit of the specification. This situation leaves room for many different interpretations of key requirements. In some cases, the requirements are simple not testable.

One example is related to the AP `inbox`. A server is required to add activities posted to the `inbox` network endpoint to an `OrderedCollection`. The intent seems to be that clients can read their `inbox` collection to find posts they have received. Other actors might also be able to see public posts in other actor's inboxes.

However, the specification says implementations should filter inbox queries based on the permissions of the requester. This is reasonable. However, it allows two degenerate cases. The first is that there is no filtering, even for private messages. In other words, the implementation is not required to do *any* filtering. The other case is that *no actor* (not even the inbox owner) is allowed to view *any* inbox activities. This is the Mastodon implementation. They return an HTTP 404 (Not Found) status for all `inbox` queries. Neither behavior is desirable, but they are allowed.

t's going to be challenging to create server-independent inbox requirements tests when an AP server has no inbox (just a POST endpoint) and discards activities immediately after processing them. It's technically spec-compliant behavior (other than, maybe, the 404 status), but I doubt that was the intent of the spec authors. It's a little concerning to me that a large majority of ActivityPub instances in the AP federation operate this way.

This makes it difficult to create a test that posts an activity to an inbox and then checks that the activity was delivered to the "inbox" of the local recipients. There are also no activities in Mastodon. Therefore, there is no way to test if an activity was delivered to an inbox because it doesn't even make sense in that context.

Possibly the best that can be done is to interpret the requirement to be that an activity's `object` is visible to a recipient after an inbox endpoint post. That could be supported using the Mastodon API. Maybe this could be hidden in the Server Abstraction Layer, but I need to do more experimentation.

Note that I'm using Mastodon as an example, but there are a family of servers that are similar (most of them inspired by or emulating Mastodon behavior).

## Complex Server Deployments

Some of the most popular servers have relatively complex deployment architectures. The architectures make sense for scaling performance. However, they make testing more complicated and slow. The extra cache and job scheduling processes (for example) have no relevance to AP or federation-related testing (since we're not doing scaling tests). If the server implementation has a modular architecture, it may be possible to replace some of the components with stubs for testing. However, from what I've seen so far, the large servers don't tend be modular so this probably isn't an option. This is another challenge that needs more experimentation to explore possible solutions.

## Asynchronous Activity Processing

Many servers will accept a message and then pass it to an asynchronous work queue for further processing. Depending on the server, little or no validation is done prior to handing it off to the work queue. If the activity is later rejected there's no feedback to the publisher.

In some cases, the tests must poll for data to finish processing. Given these servers won't have much data and no other users, hopefully the asynchronous processing finishes in a reasonable amount of it. It may not be possible to detect a rejected activity other than with a timeout (which will slow down the test suite).
## Interoperability Testing

This test suite focuses on ActivityPub (AP) compliance. However, that's not what many developers want. Most servers implement a very limited subset of ActivityPub (and ActivityStreams 2). In many cases, the developers care less about AP compliance and more about how to interoperate with some specific server implementations (that may not be compliant themselves). The tests in this suite will not be especially useful for that purpose, but the framework could potentially be used to support interoperability testing, *if* baseline interoperability requirements exist.

These requirements will necessarily be more specific than a general "Fediverse" test suite. I believe they will need to be focussed on relatively narrow application domains (possibly layered to some extent). A *interoperability profile* would be defined for these domains. These profiles will typically be more restrictive than ActivityPub to provide their stronger interoperability support. For example, there may be profiles for federated domains like:

* Microblogging
* Media sharing
* Forums
* Event Management
* Q&A sites
* Fitness Tracking
* Code Forges

To some extent, this is what the [ForgeFed](https://forgefed.org/) is working towards for code forge federation. There may even be multiple, competing interoperability profiles for a domain. I'm envisioning the profile development as collaborative, living, community efforts rather than static official documents from a standards organization.

Given these profiles, it create opportunities for effective automated interoperability testing. Rather than testing every server against every other server, each server can be tested against a known baseline knowing that other servers have been tested in a consistent manner.

---
[Table of Contents](toc.md)
