# How to use Docs as a simple CMS

Source : https://docs.suite.anct.gouv.fr/docs/0b65cc5b-2d72-408a-b5c1-0ff8d2a7a479/

This is experimental, feedbacks are more than welcome at <sylvain.zimmer@beta.gouv.fr>

Docs has a few features that are very useful for a CMS:

* User-friendly editor

* Access management

* Image upload

* Subpages for content structure

It can't be used to build a full website but for content pages or blog articles it could be a great fit.

# How to write content

## Metadata

Pages or Articles usually need metadata attached. Docs doesn't support this natively beyond the title so we implement a Markdown-like "[frontmatter](https://github.com/Kernix13/markdown-cheatsheet/blob/master/frontmatter.md)" on top of documents.

See [an example](https://docs.suite.anct.gouv.fr/docs/2b04cc16-fa34-4f50-a8e3-ee3e073d226e/).

It looks like this:

```javascript
---
key1: value1
key2: value2
---

[ ... your Docs content ... ]
```

The supported keys depend on the rendering library, but **docs2dsfr** uses "path", "summary", "status", "date", etc.

## Supported blocks

Custom blocks (from BlockNote.js) are [not supported yet](https://github.com/suitenumerique/docs/pull/1213#issuecomment-3179028084) (that includes Divider, CallOut).

Exact block support and syntax depends on the rendering library.

### docs2dsfr (used by ST Home)

* All inline formatting (bold, text color, ...) is OK

* Titles, images, quotes, lists, tables are OK

* We added support for a "HTML block" for [DSFR Accordion groups](https://vue-ds.fr/composants/DsfrAccordionsGroup) : ([Example](https://docs.suite.anct.gouv.fr/docs/c803cad1-c1e7-4a63-8367-5c6bf1a48d6c/))

```javascript
<accordion-list>
* First label
Contents
As many blocks here as you want (except lists)
* Second label
Contents
</accordion-list>
```

## General advice

* Don't forget to set filenames on uploaded images, they will be used as "alt" attributes.

* Set your document as publicly visible (but not editable of course)

* Page-specific CSS is fine to add at render to tweak the style (easier than hacks in the doc)

# Examples

* <https://suiteterritoriale.anct.gouv.fr/actualites>

  * CMS : <https://docs.suite.anct.gouv.fr/docs/a416352b-17e1-4893-82e7-fb77a4dde5b9/>

* <https://suiteterritoriale.anct.gouv.fr/services>

  * CMS : <https://docs.suite.anct.gouv.fr/docs/3ca3cc7a-405a-418b-84b4-2075492713b8/>

  * **Note**: this one demonstrates how you can use multiple Docs page for a single final page

# Technical details

## Dependencies

* An instance of Docs

* A library that will fetch and render the content.

## docs2dsfr ([GitHub](https://github.com/suitenumerique/st-home/tree/main/src/lib/docs2dsfr))

This is a first rendering implementation using [React DSFR](https://react-dsfr.codegouv.studio/) but any other target could be supported.

It fetches lossy HTML from Docs ([example for this current doc!](https://docs.suite.anct.gouv.fr/api/v1.0/documents/0b65cc5b-2d72-408a-b5c1-0ff8d2a7a479/content/?content_format=html)), parses it using [rehype](https://github.com/rehypejs/rehype) and translates it to DSFR [components](https://github.com/suitenumerique/st-home/blob/main/src/lib/docs2dsfr/components.tsx) whenever possible.

For convenience it caches the requests to Docs every hour but this could be improved.

It fetches HTML and not Markdown from Docs because:

* HTML is the first-level export format in BlockNote.js. The Markdown export is actually [converted](https://github.com/TypeCellOS/BlockNote/blob/8a8c5c5e0e961c3856e8bd6fbb70fe09dfc18d6f/packages/core/src/api/exporters/markdown/markdownExporter.ts#L30) from the HTML one.

* MDX in Next.js compiles to JSX and requires a full JavaScript interpreter, which is a security risk.

* Some (more) information is lost in Markdown compared to HTML.

## TODO

* Fix BlockNote HTML exports for toggleable elements ([Issue](https://github.com/TypeCellOS/BlockNote/issues/1936))

* ~~Merge content export in Docs,~~ with custom blocks support ([Issue](https://github.com/suitenumerique/docs/pull/1213))

* Support more DSFR elements (**CallOut** natively, others via "HTML blocks")

* Check if we could go further and have custom BlockNote blocks for metadata and explicit DSFR blocks

* More rehype plugins to clean & customize HTML ?

* Because Docs doesn't always save content to its backend right away, it can take a few seconds for the right content to appear, resulting in a poor user experience for editors who want to preview quickly (easiest way seems to be to close the doc or switch to another subpage?)
