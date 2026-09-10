import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export default function Blog() {
  const navigate = useNavigate();

  useEffect(() => {
    navigate('/blog', { replace: true });
  }, [navigate]);

  return null;
}
