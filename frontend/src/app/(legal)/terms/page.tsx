import type { Metadata } from "next";
import Link from "next/link";
import { ContactLinks, LegalPage, List, Section } from "@/components/legal";
import { SITE } from "@/lib/site";

export const metadata: Metadata = {
  title: `Terms of Service — ${SITE.name}`,
  description: `Terms for using the ${SITE.name} hosted demo at ${SITE.domain}.`,
};

const TOC = [
  { id: "acceptance", title: "Acceptance of terms" },
  { id: "service", title: "What the service is" },
  { id: "permitted-use", title: "Permitted use" },
  { id: "prohibited", title: "Prohibited activities" },
  { id: "your-content", title: "Your content and responsibilities" },
  { id: "ip", title: "Intellectual property" },
  { id: "third-party", title: "Third-party websites and services" },
  { id: "availability", title: "Availability and changes" },
  { id: "experimental", title: "Experimental software and beta features" },
  { id: "warranty", title: "No warranties" },
  { id: "liability", title: "Limitation of liability" },
  { id: "termination", title: "Suspension and removal" },
  { id: "changes", title: "Changes to these terms" },
  { id: "law", title: "Governing law" },
  { id: "contact", title: "Contact" },
];

export default function TermsPage() {
  return (
    <LegalPage
      path="/terms"
      title="Terms of Service"
      toc={TOC}
      intro={
        <>
          These terms apply to the hosted {SITE.name} demo at <strong className="text-fog-100">{SITE.domain}</strong> (the &quot;Service&quot;). {SITE.name} is a personal,
          non-commercial open-source project run by its maintainer (&quot;we&quot;, &quot;us&quot;). The source code is licensed separately under the Apache License 2.0.
        </>
      }
      summary={[
        "It's a free, public demo with no accounts. Anything you import is visible to — and can be deleted by — every other visitor.",
        "Only upload code you are allowed to share, and never upload secrets, personal data or confidential code.",
        "Don't attack the service or try to escape the COBOL sandbox. Report security issues privately instead.",
        "Generated code and verification results are evidence for the inputs tested, not a guarantee. Review everything before you rely on it.",
        "The demo can change, be reset or go offline at any time. Japanese law applies.",
      ]}
    >
      <Section id="acceptance" n={1} title="Acceptance of terms">
        <p>
          By accessing or using the Service you agree to these terms, our <Link href="/privacy">Privacy Policy</Link> and our <Link href="/disclaimer">Disclaimer</Link>. If you
          don&apos;t agree, please don&apos;t use the Service. If you use the Service on behalf of an organisation, you confirm you are allowed to accept these terms for it.
        </p>
      </Section>

      <Section id="service" n={2} title="What the service is">
        <p>
          The Service lets you import COBOL source code (from files, a ZIP archive or a public GitHub repository), analyse it, generate Python code from it, and compare the
          behaviour of the generated code with the original program compiled and run by GnuCOBOL in an isolated container.
        </p>
        <p>
          <strong>The Service is a shared public workspace.</strong> There are no user accounts or access controls: every project, file, generated service, report and
          verification result is visible to anyone who visits the site, and any visitor can delete it.
        </p>
      </Section>

      <Section id="permitted-use" n={3} title="Permitted use">
        <p>You may use the Service, free of charge, to:</p>
        <List
          items={[
            "evaluate and demonstrate COBOL analysis, Python generation and differential verification;",
            "experiment with the bundled sample project and with COBOL code you are entitled to share publicly;",
            "download the reports and generated code produced for your projects.",
          ]}
        />
        <p>For production, confidential or large-scale use, run your own copy of the open-source software instead of the hosted demo.</p>
      </Section>

      <Section id="prohibited" n={4} title="Prohibited activities">
        <p>You must not:</p>
        <List
          items={[
            "upload or import code or data you do not have the right to share, or that infringes anyone's intellectual property, privacy or other rights;",
            "upload personal data, credentials, API keys, secrets or confidential business information;",
            "attempt to break out of, probe or disable the COBOL sandbox, or use the Service to run malware, cryptocurrency miners or other code unrelated to COBOL analysis;",
            "use the Service to attack, scan or send traffic to other systems;",
            "overload the Service, for example with automated bulk imports or verification runs, or interfere with other visitors' use;",
            "delete, alter or misuse other visitors' projects except for the demo's normal purpose;",
            "upload unlawful, harmful, harassing or deceptive content, including in project names or test fixtures;",
            "use the Service in breach of any applicable law or regulation.",
          ]}
        />
        <p>
          Found a vulnerability? Please report it privately (see <a href="#contact">Contact</a>) rather than exploiting it. Good-faith, non-destructive security research that
          follows our <a href={`${SITE.repoUrl}/blob/main/SECURITY.md`} target="_blank" rel="noopener noreferrer">security policy</a> is welcome.
        </p>
      </Section>

      <Section id="your-content" n={5} title="Your content and responsibilities">
        <p>
          You keep all rights to the code and data you import (&quot;your content&quot;). By importing it, you allow us to store, process, compile and run it, and to display it
          and the results derived from it to visitors of the Service, solely to operate the Service.
        </p>
        <p>You are responsible for:</p>
        <List
          items={[
            "having the right to use and share your content in this way, including under the licence of any repository you import;",
            "making sure your content contains no personal data or confidential information;",
            "keeping your own copies — the Service is not a backup and content can be deleted at any time;",
            "reviewing, testing and validating any generated code, report or result before you use it for any purpose.",
          ]}
        />
      </Section>

      <Section id="ip" n={6} title="Intellectual property">
        <p>
          The {SITE.name} software is open source under the{" "}
          <a href={`${SITE.repoUrl}/blob/main/LICENSE`} target="_blank" rel="noopener noreferrer">
            Apache License 2.0
          </a>
          ; that licence, not these terms, governs your use of the source code. The {SITE.name} name, logo and site design may not be used in a way that suggests we endorse
          you or your product.
        </p>
        <p>
          Python code generated from your COBOL is a translation of your content; as between you and us, we claim no ownership of it. Third-party COBOL repositories shown in
          the demo remain the property of their owners and are subject to their own licences. GnuCOBOL, GitHub and other names mentioned on the site are trademarks of their
          respective owners.
        </p>
      </Section>

      <Section id="third-party" n={7} title="Third-party websites and services">
        <p>
          The Service links to and downloads from third-party services such as GitHub, and runs on third-party infrastructure (see the{" "}
          <Link href="/privacy#providers">Privacy Policy</Link>). We don&apos;t control those services and aren&apos;t responsible for their content, availability or
          practices; your use of them is governed by their own terms.
        </p>
      </Section>

      <Section id="availability" n={8} title="Availability and changes">
        <p>
          The Service is provided on a best-effort basis with no uptime commitment. We may change, limit, reset (including deleting all projects), suspend or discontinue any
          part of it at any time, with or without notice. Import limits, timeouts and other technical limits may change.
        </p>
      </Section>

      <Section id="experimental" n={9} title="Experimental software and beta features">
        <p>
          {SITE.name} was built as a hackathon project and is experimental. It supports a documented subset of COBOL; unsupported constructs are reported rather than
          translated, and features may be incomplete, change without notice or be removed. Optional AI features, where enabled, are advisory only. See the{" "}
          <Link href="/disclaimer">Disclaimer</Link> for details.
        </p>
      </Section>

      <Section id="warranty" n={10} title="No warranties">
        <p>
          To the extent permitted by applicable law, the Service and everything it produces — including analysis, business-rule documentation, generated code, verification
          results and reports — are provided <strong>&quot;as is&quot; and &quot;as available&quot;</strong>, without warranties of any kind, express or implied, including
          warranties of accuracy, completeness, reliability, availability, merchantability, fitness for a particular purpose, non-infringement, or that the Service will be
          error-free or secure.
        </p>
        <p>
          In particular, a &quot;verified&quot; result means the original and the generated program produced identical outputs <strong>for the inputs that were executed</strong>
          . It is not proof that they behave identically for all inputs.
        </p>
      </Section>

      <Section id="liability" n={11} title="Limitation of liability">
        <p>
          To the extent permitted by applicable law, we will not be liable for any indirect, incidental, special, consequential or punitive damages, or for any loss of data,
          profits, revenue, business or goodwill, arising from or related to your use of, or inability to use, the Service or anything it produces, even if we were advised
          of the possibility of such damages.
        </p>
        <p>
          Because the Service is provided free of charge, to the extent permitted by law our total liability for any claim relating to the Service is limited to direct and
          ordinary damages actually incurred, up to a maximum of JPY 10,000.
        </p>
        <p>
          Nothing in these terms excludes or limits liability that cannot be excluded or limited under applicable law — including, where the Consumer Contract Act of Japan
          applies, liability for damage caused by our intentional misconduct or gross negligence.
        </p>
      </Section>

      <Section id="termination" n={12} title="Suspension and removal">
        <p>
          We may remove any content, or restrict or block access to the Service, at any time if we reasonably believe it breaches these terms, puts the Service or other
          people at risk, or is required by law.
        </p>
      </Section>

      <Section id="changes" n={13} title="Changes to these terms">
        <p>
          We may update these terms from time to time. The &quot;Last updated&quot; date at the top shows when they last changed, and the revision history is public in the
          source repository. Continuing to use the Service after a change means you accept the updated terms.
        </p>
      </Section>

      <Section id="law" n={14} title="Governing law">
        <p>
          These terms are governed by the laws of Japan, without regard to conflict-of-law rules. This does not deprive you of the protection of any mandatory provisions of
          the law of the country where you live that cannot be overridden by agreement. If any provision of these terms is held invalid or unenforceable, the remaining
          provisions stay in effect.
        </p>
      </Section>

      <Section id="contact" n={15} title="Contact">
        <ContactLinks />
      </Section>
    </LegalPage>
  );
}
