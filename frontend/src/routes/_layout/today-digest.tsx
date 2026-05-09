import { createFileRoute } from '@tanstack/react-router';
import type { DigestPublicSchema } from '@/client';
import DigestHeader from '@/components/Digest/DigestHeader';
import DigestSections from '@/components/Digest/DigestSections';
import DigestSkeleton from '@/components/Digest/DigestSkeleton';
import DigestState from '@/components/Digest/DigestState';
import { PageContainer } from '@/components/Layout/Page';
import { useTodayDigest } from '@/hooks/useTodayDigest';

export const Route = createFileRoute('/_layout/today-digest')({
  component: TodayDigest,
  head: () => ({
    meta: [
      {
        title: "Today's AI Signal",
      },
    ],
  }),
});

type DigestBodyProps = {
  data: DigestPublicSchema | undefined;
  isLoading: boolean;
  isError: boolean;
};

function DigestBody({ data, isLoading, isError }: DigestBodyProps) {
  if (isLoading) {
    return <DigestSkeleton />;
  }

  if (isError) {
    return (
      <DigestState
        title="Could not load today's digest"
        description="Refresh the page in a moment. The digest data did not come back cleanly."
      />
    );
  }

  if (!data || data.sections.length === 0) {
    return (
      <DigestState
        title="Today's digest will appear here"
        description="Once enough fresh articles are available, the briefing will be grouped by signal area."
      />
    );
  }

  return <DigestSections sections={data.sections} />;
}

function TodayDigest() {
  const { data, isLoading, isError } = useTodayDigest();

  return (
    <PageContainer
      variant="narrow"
      spacing="none"
      className="max-w-3xl py-12 sm:py-16 md:py-20"
    >
      <DigestHeader digest={data} />
      <DigestBody data={data} isLoading={isLoading} isError={isError} />
    </PageContainer>
  );
}
