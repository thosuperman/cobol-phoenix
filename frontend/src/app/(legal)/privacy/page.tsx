import type { Metadata } from "next";
import Link from "next/link";
import { ContactLinks, FactTable, LegalPage, List, Section } from "@/components/legal";
import { SITE } from "@/lib/site";

export const metadata: Metadata = {
  title: `Privacy Policy — ${SITE.name}`,
  description: `What data the ${SITE.name} hosted demo at ${SITE.domain} processes, why, and for how long.`,
};

const TOC = [
  { id: "scope", title: "Scope and who we are" },
  { id: "collected", title: "Data we process" },
  { id: "purposes", title: "Why we process it" },
  { id: "cookies", title: "Cookies and local storage" },
  { id: "analytics", title: "Analytics" },
  { id: "logs", title: "Server logs and IP addresses" },
  { id: "providers", title: "Third-party providers" },
  { id: "ai", title: "AI-related processing" },
  { id: "retention", title: "Retention and deletion" },
  { id: "security", title: "Security" },
  { id: "transfers", title: "International data transfers" },
  { id: "rights", title: "Your rights" },
  { id: "children", title: "Children" },
  { id: "changes", title: "Changes to this policy" },
  { id: "contact", title: "Contact and privacy inquiries" },
];

export default function PrivacyPage() {
  return (
    <LegalPage
      path="/privacy"
      title="Privacy Policy"
      toc={TOC}
      intro={
        <>
          This policy explains how the hosted {SITE.name} demo at <strong className="text-fog-100">{SITE.domain}</strong> handles information. It was written from an audit of
          the site&apos;s actual code and deployment configuration, and we handle personal information in line with Japan&apos;s Act on the Protection of Personal Information
          (APPI) and other applicable laws.
        </>
      }
      summary={[
        "No accounts, no sign-up, no cookies, no analytics and no advertising trackers.",
        "Whatever you import is stored on our server and is visible to every visitor — so don't upload personal data or anything confidential.",
        "Your IP address reaches our server because that's how the internet works; we don't use it to profile you, and we don't sell or share data.",
        "The demo runs without any AI provider. If that ever changes, this page will say so first.",
        "Servers are on AWS in Singapore. Anyone can delete a project with the trash icon; ask us about anything else.",
      ]}
    >
      <Section id="scope" n={1} title="Scope and who we are">
        <p>
          The Service is a personal, non-commercial open-source project operated by its maintainer (&quot;we&quot;, &quot;us&quot;). This policy covers only the hosted demo
          at {SITE.domain}. If you run {SITE.name} yourself, you — not us — are responsible for the data your installation processes.
        </p>
      </Section>

      <Section id="collected" n={2} title="Data we process">
        <p>
          <strong>We don&apos;t ask for any personal information.</strong> There are no accounts, forms for contact details, newsletters or payments. The Service processes
          the following:
        </p>
        <FactTable
          head={["Data", "Details"]}
          rows={[
            [
              "Content you import",
              "COBOL source files, copybooks, ZIP archives, the name of a public GitHub repository and ref, project names, and test fixtures you enter. Plus everything derived from them: analysis, business rules, generated Python code, verification runs and reports.",
            ],
            [
              "Technical connection data",
              "Your IP address, the requested URL, time, and browser-supplied headers (such as user agent) are necessarily received by our server to deliver the site. See Server logs below.",
            ],
            [
              "Messages you send us",
              "If you contact us through GitHub, we see what you write and your GitHub profile, as provided by GitHub.",
            ],
          ]}
        />
        <p>
          <strong>Please don&apos;t include personal data in anything you import.</strong> The Service has no access controls, so imported content is visible to all visitors.
          If personal data ends up in a project, delete the project (trash icon on the project page) or contact us.
        </p>
      </Section>

      <Section id="purposes" n={3} title="Why we process it">
        <List
          items={[
            "To provide the Service: store, analyse, compile, run and compare your code, and show you the results.",
            "To keep the Service secure and working: prevent abuse, investigate errors and protect the sandbox.",
            "To answer you when you contact us.",
            "To comply with legal obligations.",
          ]}
        />
        <p>We don&apos;t use data for advertising, profiling, selling or training AI models, and we don&apos;t provide personal data to third parties except as described here or as required by law.</p>
      </Section>

      <Section id="cookies" n={4} title="Cookies and local storage">
        <p>
          The Service does <strong>not</strong> set cookies and does not use your browser&apos;s local storage, session storage or similar technologies. Fonts are served
          from our own domain, so loading the site does not contact font or script providers such as Google. There are no embedded third-party widgets.
        </p>
      </Section>

      <Section id="analytics" n={5} title="Analytics">
        <p>
          We don&apos;t use any analytics, tracking pixels, session recording or advertising services. We have no statistics about individual visitors. If we ever add
          analytics, we will update this policy before doing so.
        </p>
      </Section>

      <Section id="logs" n={6} title="Server logs and IP addresses">
        <p>
          Every web request reaches our server with your IP address — that&apos;s required to send the page back. Our HTTPS server (Caddy) is configured without access
          logging. The application components write operational logs (for example request method, path, response status, time and error details) to the server&apos;s
          container logs. Because requests pass through an internal proxy, these logs normally record internal addresses rather than yours, but they may incidentally
          contain an IP address or other request details.
        </p>
        <p>
          We use logs only to run, debug and secure the Service. They stay on our server, are not shared, and are deleted when the containers are recreated during
          maintenance or redeployment. Our infrastructure provider may also process network-level data to operate and protect its platform.
        </p>
      </Section>

      <Section id="providers" n={7} title="Third-party providers">
        <FactTable
          head={["Provider", "Role", "Data involved"]}
          rows={[
            ["Amazon Web Services (Lightsail, Route 53)", "Server hosting in Singapore; DNS for our domain", "All data described in this policy is stored and processed on this infrastructure"],
            ["GitHub", "Source of repository imports; hosts our source code and contact channel", "When you import a repository, our server downloads it from GitHub — GitHub sees our server, not you. If you contact us there, GitHub's privacy statement applies."],
            ["Let's Encrypt", "Issues our HTTPS certificate", "Only our domain name; no visitor data"],
          ]}
        />
        <p>
          Links to other websites (such as GitHub or the source repositories of imported projects) take you to services with their own privacy policies.
        </p>
      </Section>

      <Section id="ai" n={8} title="AI-related processing">
        <p>
          <strong>The hosted demo does not send any data to AI or large-language-model providers.</strong> Business-rule explanations are produced by deterministic code on
          our server; the sidebar in the workspace shows &quot;AI explanations: deterministic&quot;. Code analysis and code generation never use AI.
        </p>
        <p>
          The software can optionally be configured with an external AI provider for rule explanations. If we enable this on the hosted demo, we will update this policy
          first. In that mode, when someone clicks <em>Explain</em> on a rule, only that rule&apos;s extracted facts and the cited COBOL source lines would be sent to the
          configured provider — never your IP address or other files — and the response would be labelled as advisory.
        </p>
      </Section>

      <Section id="retention" n={9} title="Retention and deletion">
        <FactTable
          head={["Data", "How long"]}
          rows={[
            ["Imported content and results", "Until any visitor deletes the project, or we remove it or reset the demo. We may reset the demo at any time and will delete everything when the demo ends."],
            ["Operational logs", "Until the containers are recreated during maintenance or redeployment."],
            ["Messages on GitHub", "As long as the issue or advisory exists on GitHub."],
          ]}
        />
        <p>
          To delete a project yourself, open it and use the trash icon at the top right; this removes its files, analysis, generated code and verification results from our
          database and disk. Copies may remain in short-lived server backups or snapshots, if any, until they are overwritten.
        </p>
      </Section>

      <Section id="security" n={10} title="Security">
        <p>We take reasonable technical and organisational measures appropriate for a small demo, including:</p>
        <List
          items={[
            "HTTPS for all traffic, with HSTS;",
            "only the HTTPS server is reachable from the internet; the application and database listen on internal interfaces;",
            "imported COBOL is treated as data and only ever compiled and run in a sandbox container with no network, a read-only file system, dropped privileges and resource limits;",
            "upload validation (size and file-type limits, path checks, no symbolic links) and secrets kept out of the source code;",
            "automated security checks in our development pipeline.",
          ]}
        />
        <p>
          No system is perfectly secure, and the Service is deliberately a public, shared workspace — another reason not to upload anything sensitive. Our full threat model
          is in the <a href={`${SITE.repoUrl}/blob/main/SECURITY.md`} target="_blank" rel="noopener noreferrer">security policy</a>.
        </p>
      </Section>

      <Section id="transfers" n={11} title="International data transfers">
        <p>
          The Service is operated from Japan, and its servers are located in <strong>Singapore</strong> ({SITE.hosting}). Data you send to the Service is therefore stored and
          processed in Singapore, and may be accessed from Japan for maintenance.
        </p>
        <p>
          For transparency under the APPI: Singapore has a comprehensive personal data protection law, the Personal Data Protection Act 2012, supervised by the Personal Data
          Protection Commission. AWS provides the infrastructure under its customer agreement and data processing terms, which commit it to security measures and to not
          accessing customer content except as needed to provide its services or comply with law. If you are outside Japan, your data is transferred to Singapore and Japan
          when you use the Service.
        </p>
      </Section>

      <Section id="rights" n={12} title="Your rights">
        <p>
          Under the APPI and other applicable laws, you may ask us to disclose, correct, add to or delete personal data we hold about you, to stop using it or providing it
          to third parties, and to disclose records of any third-party provision. Depending on where you live, you may have similar or additional rights, such as objecting
          to processing or lodging a complaint with a data protection authority (in Japan, the Personal Information Protection Commission).
        </p>
        <p>
          Because the Service has no accounts, we usually cannot link data to a particular person. To help us find it, tell us which project or request is involved. We will
          respond within a reasonable time and may need to confirm that the request is genuinely yours. We don&apos;t charge for these requests.
        </p>
      </Section>

      <Section id="children" n={13} title="Children">
        <p>The Service is a developer tool and is not directed at children. Please don&apos;t upload information about children.</p>
      </Section>

      <Section id="changes" n={14} title="Changes to this policy">
        <p>
          We will update this policy when the Service&apos;s data handling changes — for example before enabling analytics or an AI provider. The &quot;Last updated&quot; date
          shows the latest revision, and every change is visible in the public source repository.
        </p>
      </Section>

      <Section id="contact" n={15} title="Contact and privacy inquiries">
        <ContactLinks />
        <p>
          See also our <Link href="/terms">Terms of Service</Link> and <Link href="/disclaimer">Disclaimer</Link>.
        </p>
      </Section>
    </LegalPage>
  );
}
