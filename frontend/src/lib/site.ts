/** Site-wide facts used by the legal pages. Keep these in sync with the deployment (deploy/lightsail.env.example). */
export const SITE = {
  name: "COBOL Phoenix",
  domain: "cobol.beauty",
  url: "https://cobol.beauty",
  repoUrl: "https://github.com/thosuperman/cobol-phoenix",
  /** The only contact channels we publish: the project's GitHub issues and private security advisories. */
  contactUrl: "https://github.com/thosuperman/cobol-phoenix/issues",
  securityUrl: "https://github.com/thosuperman/cobol-phoenix/security/advisories/new",
  hosting: "Amazon Web Services (AWS) Lightsail, Asia Pacific (Singapore) region",
  legalUpdated: "11 November 2026",
} as const;
