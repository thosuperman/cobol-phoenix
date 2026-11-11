import type { Metadata } from "next";
import Link from "next/link";
import { ContactLinks, LegalPage, List, Section } from "@/components/legal";
import { SITE } from "@/lib/site";

export const metadata: Metadata = {
  title: `Disclaimer — ${SITE.name}`,
  description: `Limits of the ${SITE.name} demo, its generated code, verification results and optional AI features.`,
};

const TOC = [
  { id: "project", title: "A personal, experimental project" },
  { id: "no-guarantee", title: "No guarantee" },
  { id: "verification", title: "What “verified” means" },
  { id: "generated-code", title: "Generated code and reports" },
  { id: "not-advice", title: "Not professional advice" },
  { id: "ai", title: "AI features" },
  { id: "third-party", title: "Third-party code and content" },
  { id: "contact", title: "Contact" },
];

export default function DisclaimerPage() {
  return (
    <LegalPage
      path="/disclaimer"
      title="Disclaimer"
      toc={TOC}
      intro={
        <>
          {SITE.name} tries hard to be honest about what it knows and what it doesn&apos;t. This page sets out those limits. It supplements our{" "}
          <Link href="/terms">Terms of Service</Link>.
        </>
      }
      summary={[
        "This is a personal hobby project built for a hackathon — an experiment, not a commercial product.",
        "Results can be wrong. Treat every output as a starting point to review, not a finished answer.",
        "“Verified” covers only the inputs that were actually run, not every possible input.",
        "Any AI-written text is advisory, may contain errors and must be checked independently.",
      ]}
    >
      <Section id="project" n={1} title="A personal, experimental project">
        <p>
          {SITE.name} is a personal hobby project and experiment, originally built for the Kiroween 2026 hackathon. It is provided for informational, educational and
          experimental purposes. It is not a commercial product, it comes with no support commitment, and it is not affiliated with or endorsed by any employer, the
          hackathon organisers or the owners of the third-party projects it is demonstrated on.
        </p>
      </Section>

      <Section id="no-guarantee" n={2} title="No guarantee">
        <p>
          To the extent permitted by law, we make no guarantee about the accuracy, completeness, reliability, security, availability or fitness for a particular purpose of
          the Service or anything it produces. The hosted demo may be slow, reset, changed or offline at any time. Use it at your own risk.
        </p>
      </Section>

      <Section id="verification" n={3} title={"What “verified” means"}>
        <p>
          A <strong>VERIFIED</strong> case means the original COBOL program, compiled and run by GnuCOBOL, and the generated Python produced identical outputs for that specific
          input. A run with all cases verified is evidence of equivalence <strong>for the inputs executed</strong> — not a proof that the programs behave identically for all
          inputs.
        </p>
        <List
          items={[
            "Statement coverage and mutation scores measure how thorough the tests were; they don't guarantee the absence of differences.",
            "Results reflect GnuCOBOL's behaviour with the dialect options used by the Service. Other compilers, such as IBM Enterprise COBOL, and other options can behave differently.",
            "Unsupported COBOL constructs are reported and not translated; a project with unsupported parts is not fully modernised.",
            "File I/O, databases, CICS and other environment-specific behaviour are outside what the Service can verify.",
          ]}
        />
      </Section>

      <Section id="generated-code" n={4} title="Generated code and reports">
        <p>
          Generated Python services, business-rule documentation, dependency graphs, complexity scores and reports are produced automatically. They may contain errors or
          omissions and have not been reviewed by a person. Before using any of them in production, you should have qualified people review the code, test it against your
          own data and requirements, and run your normal security, compliance and change-control processes.
        </p>
      </Section>

      <Section id="not-advice" n={5} title="Not professional advice">
        <p>
          Nothing on the site is legal, financial, insurance, actuarial, accounting or other professional advice. The sample &quot;Phoenix Mutual&quot; project, its rates and
          rules are fictional and exist only to demonstrate the software. Business rules extracted from code describe what the code does, not whether it is correct, fair or
          compliant.
        </p>
      </Section>

      <Section id="ai" n={6} title="AI features">
        <p>
          Code analysis, code generation and verification in {SITE.name} are deterministic — no AI writes the code or decides the results. The software can optionally be
          configured to produce AI-written explanations of business rules; on the hosted demo this is currently turned off (see the{" "}
          <Link href="/privacy#ai">Privacy Policy</Link>). Wherever AI features are enabled:
        </p>
        <List
          items={[
            "AI-generated content may be inaccurate, incomplete or misleading, even when it sounds confident;",
            "it is labelled as advisory and never replaces the source citations, deterministic analysis or verification results;",
            "you should verify any AI output independently against the cited COBOL source before relying on it;",
            "AI providers, models and their behaviour may change, and AI features may become unavailable at any time.",
          ]}
        />
      </Section>

      <Section id="third-party" n={7} title="Third-party code and content">
        <p>
          Projects imported by visitors and the public repositories used for demonstration belong to their respective owners and are subject to their own licences. We
          don&apos;t review, endorse or take responsibility for content imported by visitors. Links to other websites are provided for convenience only.
        </p>
      </Section>

      <Section id="contact" n={8} title="Contact">
        <p>Spotted an error, a wrong result or a problem with content on the site? Please let us know.</p>
        <ContactLinks />
      </Section>
    </LegalPage>
  );
}
