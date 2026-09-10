import { useExport } from '../hooks/useExport';
import MetadataHero from '../components/metadata/MetadataHero';
import MetadataForm from '../components/metadata/MetadataForm';

export default function Metadata() {
  const { result, loading, progress, error, startExport, reset, retry, cancelExport, backendStatus } = useExport();

  return (
    <>
      <MetadataHero />
      <MetadataForm
        onExport={startExport}
        loading={loading}
        progress={progress}
        result={result}
        error={error}
        reset={reset}
        retry={retry}
        cancelExport={cancelExport}
        backendStatus={backendStatus}
      />
    </>
  );
}
