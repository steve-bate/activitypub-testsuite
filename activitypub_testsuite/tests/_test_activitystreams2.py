#
# Activity Streams
#

# It's not clear how much of this is testable.

# AS2 Section 2. If a property has an array value, the absence
# of any items in that array must be represented by omitting
# the property entirely or by setting the value to null.

# AS2 2.1.3 When a JSON-LD enabled Activity Streams 2.0
# implementation encounters a JSON document identified using the
# "application/activity+json" MIME media type, and that document
# does not contain a @context property whose value includes a
# reference to the normative Activity Streams 2.0 JSON-LD @context
# definition, the implementation must assume that the normative
# @context definition still applies.

# AS2 2.2 - when an IRI that is not also a URI is given
# for dereferencing, it must be mapped to a URI using the
# steps in Section 3.1 of [RFC3987] and (2) when an IRI is
# serving as an "id" value, it must not be so mapped.

# AS2 Section 2.3 - All properties with date and time
# values must conform to the "date-time" production in [RFC3339] with
# the one exception that seconds may be omitted.
#
# An uppercase "T" character must be used to separate date and time,
#  and an uppercase "Z" character must be used in the absence
# of a numeric time zone offset.

# AS2 4.2 - To promote interoperability, Activity Streams
# 2.0 implementations must only use link relations that are
# syntactically valid in terms of both the [RFC5988]
# and [HTML5] definitions.
