import Shell from './Shell';
import { info } from './info';
import Spc from './Spc';

export default function App() {
 return <Shell info={info} repo="graficas-de-control" page="graficas-de-control">{lang => <Spc lang={lang}/>}</Shell>;
}
