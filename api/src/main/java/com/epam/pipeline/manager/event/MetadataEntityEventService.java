/*
 * Copyright 2017-2019 EPAM Systems, Inc. (https://www.epam.com/)
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.epam.pipeline.manager.event;

import com.epam.pipeline.entity.security.acl.AclClass;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class MetadataEntityEventService implements EntityEventService {

    private final EventManager eventManager;

    @Override
    public AclClass getSupportedClass() {
        return AclClass.METADATA_ENTITY;
    }

    @Override
    public void updateEventsWithChildrenAndIssues(final Long id) {
        eventManager.addUpdateEventsForIssues(id, AclClass.METADATA_ENTITY);
        eventManager.addUpdateEvent(EventObjectType.METADATA_ENTITY.name().toLowerCase(), id);
    }
}
