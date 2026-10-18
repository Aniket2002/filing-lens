# Attribution and licensing

Original code: Copyright 2026 Aniket Bhardwaj. Licensed under
AGPL-3.0-or-later; see [LICENSE](LICENSE). PyMuPDF is an AGPL/commercial dependency;
this project's open-source distribution uses the AGPL option.

Annual reports belong to their original issuers. The repository does not claim
ownership of those filings or grant a blanket license to them. Full PDFs are
downloaded from the explicitly attributed public URLs and kept outside version
control. Numeric statement facts, short evaluation excerpts, and source links are
retained to make the benchmark auditable.

Pretrained model weights are downloaded from Hugging Face, not redistributed:

- [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2): Apache-2.0.
- [MS MARCO MiniLM cross-encoder](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2): Apache-2.0.
- [FLAN-T5-small](https://huggingface.co/google/flan-t5-small): Apache-2.0, optional generation experiment.

Model repositories and immutable revisions are recorded in `data/model-lock.json`
and `data/generator-lock.json`. Dependency licenses remain with their respective
authors. No affiliation with the issuers, the SEC, AnnualReports.com, Google,
Microsoft, or Hugging Face is implied.
