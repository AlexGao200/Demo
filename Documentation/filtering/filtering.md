# Filtering

### Filter Dimension

A **filter dimension** is one dimension of a filter system. It consists of multiple filter values that can be selected individually or in combination, depending on the operation.

Attributes:
- Name: A unique identifier for the filter category
- Selection Type: Single-select or Multi-select
- Data Type: String, Number, Date, etc.

Example:
- Filter Dimension: Body Part
- Filter values: Hip, Knee, Spine

### Filter System
A **filter system** is a collection of multiple filter categories used to categorize and retrieve information.
Example: A filter system may have several filter categories:
- Country
- Medical Specialty
- Body Part

By default, organizations have the following filter dimensions:
- Medical Specialty (e.g. orthopedics, cardiology)
- Body part (e.g. knee, hip, heart)

Organizations can also other filter dimensions to their databases. Examples include
- Body system
- Surgery type
