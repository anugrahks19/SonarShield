import { Client } from '@gradio/client';
import { createGateway } from '../server/gateway.mjs';

export default createGateway({ connect: (space, options) => Client.connect(space, options) });
