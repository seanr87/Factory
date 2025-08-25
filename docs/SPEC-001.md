# SPEC-001-Study Repo Factory for OHDSI Network Studies
## Background

This project is designed to support a team at Johns Hopkins coordinating OHDSI network studies. The goal is to create a GitHub repository template system that allows a study lead to quickly spin up a new study repository with predefined templates and structures. A central "Factory" portfolio project will keep track of all the studies and their associated data partners.

## Dependency & Source of Truth 
This implementation MUST follow **SPEC-002_briefing-packet.md**. All coding agents (e.g., Claude Code) must ingest `briefing.zip` and cite packet paths in proposals and PRs.

## Requirements

### Must have:

- Enable a study lead to generate a new study repository from a template using a simple command or automated GitHub Action.

- Each study repository should come with an associated project board that guides the study lead through each phase of the study.

- The central “Factory” portfolio project must automatically update its overall status based on the progress of each individual study repo.

- The study repositories must include templates and initial content that are auto-filled during the provisioning process.

### Should have:

- The Factory portfolio project should display a column with the last updated date and a link to the last updated file or issue for each study.

- Highlight any study repos that have not been updated in over a month with a “delinquent” tag.

- Automatically record a start date for each study when the repo is created.

- Each study issue in the portfolio should include a link to the study repo and a chart or list showing the progress of different data partners.

- Provide a link to the study’s project board within the portfolio issue.

- Ensure that study project issues are displayed in order of the study phases, and offer a separate view for tracking data partner progress.

- Appropriately colored statuses for both studies and data partners.

## Method

We will implement the system in a modular fashion, using GitHub Actions for repository creation and a custom GitHub App for updating the portfolio project. This modular design will ensure that the architecture is easy to extend or modify in the future. Although the initial code generation will be done by an LLM, the system will be documented and structured so that it is easy for human developers to maintain going forward. 

We will use the best technologies for the job. If there's no difference in performance, we'll use Python.

## Implementation

We will set up GitHub Actions to handle the template-based repository creation. A GitHub App with organization-level permissions will manage the portfolio updates in real time. The app will ensure that the project boards and portfolio columns are updated according to the specified requirements. Documentation will be included so that the system is easy to understand and modify.

## Milestones

We will define milestones for 
1. Completing the GitHub Actions setup
2. deploying the GitHub App
3. validating that the portfolio project updates correctly. 

Each milestone will include testing to ensure everything works as expected.

## Gathering Results

After implementation, we will evaluate whether all requirements have been met and verify that the system is functioning smoothly. We will also review the documentation to ensure that future maintenance is straightforward.