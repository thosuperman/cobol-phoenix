/** Site-wide facts used by the legal pages. Keep these in sync with the deployment (docs/deployment.md). */
export const SITE = {
  name: "COBOL Phoenix",
  domain: "cobol.beauty",
  url: "https://cobol.beauty",
  repoUrl: "https://github.com/thosuperman/cobol-phoenix",
  /** The only contact channels we publish: the project's GitHub issues and private security advisories. */
  contactUrl: "https://github.com/thosuperman/cobol-phoenix/issues",
  securityUrl: "https://github.com/thosuperman/cobol-phoenix/security/advisories/new",
  hosting: "a virtual private server operated by Cloudfly Corporation, Vietnam",
  legalUpdated: "25 November 2026",
} as const;
